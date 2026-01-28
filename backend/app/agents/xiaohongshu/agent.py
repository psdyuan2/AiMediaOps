"""
小红书智能体 - 基于MCP协议的小红书操作自动化

本模块提供基于Model Context Protocol (MCP)的小红书操作智能体。
通过MCP协议与小红书操作服务通信，实现稳定可靠的小红书自动化运营。

主要功能：
1. 简化登录流程：二维码获取、终端展示、用户交互
2. 小红书内容管理：发布图文、发布视频、内容搜索
3. 互动操作：点赞、评论、收藏、浏览
4. 用户管理：登录状态检查、账户信息获取

设计原则：
- 奥卡姆剃刀原则：保持简洁高效，避免过度设计
- 关注点分离：MCP客户端与Agent逻辑分离
- 异步优先：全面使用async/await提高并发性能
- 错误容忍：完善的错误处理和重试机制
"""

import asyncio
import base64
import json
import os
import random
from datetime import time, datetime
from typing import Any, Dict, List, Optional, Union
from app.data.constants import LogBindType
# 日志配置导入 - 使用统一的日志管理模块
from app.core.logger import logger
from app.utils.poster_creator import create_poster
from app.utils.path_utils import (
    ensure_user_task_dirs,
    get_user_source_file_path,
    get_user_images_path,
    get_user_notes_file_path,
    get_user_notes_path
)
from app.data.constants import POSTER_WORD_COUNT, DEFAULT_KNOWLEDGE_PATH, DEFAULT_IMAGE_PATH, DEFAULT_NOTES_PATH

# MCP协议相关导入
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("mcp库未安装，XiaohongshuAgent功能受限")

# Pydantic模型导入
from pydantic import BaseModel, Field

# 项目内部导入
from app.agents.base import BaseAgent, BaseAgent as BaseAgentTool
from app.core.context import Context
from app.core.llm import LLMService
from app.core.prompts import PromptEngine, prompt_engine

# 导入MCP客户端
from app.agents.xiaohongshu.MCP_client import MCPClient


class XHSContent(BaseModel):
    """
    小红书内容生成模型

    用于LLM生成小红书帖子内容的结构化输出
    """
    title: str = Field(description="帖子标题，不超过20个中文字符")
    subtitle: str = Field(description="帖子副标题，不超过20个中文字符")
    content: str = Field(description="帖子正文内容，不超过500字")
    tags: List[str] = Field(description="话题标签列表，最多5个", default_factory=list)
    image_suggestions: List[str] = Field(description="图片内容建议描述", default_factory=list)

    def validate_content(self) -> bool:
        """验证内容是否符合小红书要求"""
        # 简单验证：标题长度不超过20个字符
        if len(self.title) > 20:
            return False
        # 内容长度不超过1000个字符
        if len(self.content) > 500:
            return False
        return True


class XHSComment(BaseModel):
    """
    小红书评论生成模型

    用于LLM生成小红书评论内容的结构化输出
    """
    content: str = Field(description="评论内容，不超过200字")
    tone: str = Field(description="评论语气，如友好、专业、幽默、鼓励等", default="友好")
    is_reply: bool = Field(description="是否为回复评论", default=False)
    target_comment_id: Optional[str] = Field(description="回复的目标评论ID（如果是回复评论）", default=None)

    def validate_content(self) -> bool:
        """验证评论内容是否符合小红书要求"""
        # 评论内容长度不超过200个字符
        if len(self.content) > 200:
            return False
        return True


class XiaohongshuAgent(BaseAgent):
    """
    小红书智能体 - 基于MCP协议的小红书操作自动化

    继承BaseAgent，集成LLM服务和MCP客户端，提供：
    1. 简化的登录流程管理
    2. 小红书操作工具封装
    3. LLM驱动的意图解析和内容生成
    4. 上下文感知的任务执行

    使用示例：
        agent = XiaohongshuAgent(context, llm_service)
        await agent.run()
    """

    def __init__(
            self,
            context: Context,
            llm: LLMService,
            user_name: str,
            user_id: str,
            task_id: str,
            user_query: str=None,
            user_topic: str=None,
            user_style: str=None,
            user_target_audience: str=None,
            knowledge_base_path: str = DEFAULT_KNOWLEDGE_PATH,
            mcp_server_url: str = "http://localhost:18060/mcp",
            **kwargs
    ) -> None:
        """
        初始化小红书智能体

        Args:
            context: 上下文对象，包含系统状态和执行计划
            llm: LLM服务，用于结构化推理和内容生成
            mcp_server_url: MCP服务器URL，默认为本地18060端口
        """
        super().__init__(context, llm)

        # 初始化MCP客户端
        self.mcp_client = MCPClient(mcp_server_url)
        self.is_connected = False
        self.user_name = user_name
        self.user_id = user_id
        self.task_id = task_id
        self.knowledge_base_path = knowledge_base_path
        self.user_query = user_query
        self.user_topic = user_topic
        self.user_style = user_style
        self.user_target_audience = user_target_audience
        self.comment_note_nums = kwargs.get('comment_note_nums', 1)
        # 任务模式和互动笔记数量
        from app.data.constants import TaskMode
        mode_str = kwargs.get('mode', TaskMode.STANDARD.value)
        if isinstance(mode_str, str):
            try:
                self.mode = TaskMode(mode_str)
            except ValueError:
                logger.warning(f"无效的模式值: {mode_str}，使用默认值 {TaskMode.STANDARD.value}")
                self.mode = TaskMode.STANDARD
        elif isinstance(mode_str, TaskMode):
            self.mode = mode_str
        else:
            self.mode = TaskMode.STANDARD
        self.interaction_note_count = kwargs.get('interaction_note_count', 3)
        self.interaction_note_count = max(1, min(5, int(self.interaction_note_count))) if self.interaction_note_count else 3
        # 登录状态
        self.is_logged_in = False
        self.login_retry_count = 0
        self.max_login_retries = 3

        # 初始化用户任务目录
        if not ensure_user_task_dirs(self.user_id):
            logger.warning(f"用户 {self.user_id} 任务目录初始化失败，某些功能可能受影响")

        logger.info(f"小红书智能体初始化完成，MCP服务器: {mcp_server_url}")

    async def ensure_connected(self) -> None:
        """
        确保MCP连接已建立

        如果未连接，则建立连接；如果已连接，则检查连接是否仍然有效。

        Raises:
            ConnectionError: 连接失败时抛出
        """
        # 检查连接状态：不仅要检查 is_connected 标志，还要检查实际的 session 是否存在
        if not self.is_connected or not self.mcp_client.session:
            try:
                # 如果之前有连接但 session 丢失了，重置状态
                if self.is_connected and not self.mcp_client.session:
                    logger.warning("MCP连接状态不一致，重新建立连接")
                    self.is_connected = False
                
                await self.mcp_client.connect()
                self.is_connected = True
                logger.info("MCP连接已建立")
            except Exception as e:
                self.is_connected = False
                raise ConnectionError(f"建立MCP连接失败: {e}")

    async def ensure_logged_in(self) -> bool:
        """
        确保已登录小红书

        简化登录流程：
        1. 检查当前登录状态
        2. 如果未登录，获取二维码并引导用户扫码
        3. 等待用户确认后验证登录状态
        4. 如果登录失败，重试（最多3次）

        Returns:
            bool: 是否成功登录

        Raises:
            RuntimeError: 登录失败达到最大重试次数时抛出
        """
        # 检查当前登录状态
        try:
            status = await self.mcp_client.check_login_status()
            if status.get("is_logged_in", False):
                self.is_logged_in = True
                logger.info("小红书已登录")
                return True
        except Exception as e:
            logger.warning(f"检查登录状态失败: {e}")

        # 未登录，开始登录流程
        logger.info("小红书未登录，开始登录流程...")

        while self.login_retry_count < self.max_login_retries:
            try:
                # 获取登录二维码
                logger.info("正在获取登录二维码...")
                qrcode_info = await self.mcp_client.get_login_qrcode()

                # 保存二维码图片
                if qrcode_info.get("base64_image"):
                    filepath = self.mcp_client.save_qrcode_image(qrcode_info["base64_image"])
                    logger.info(f"二维码已保存至: {filepath}")
                    logger.info("请使用小红书App扫描二维码登录")
                else:
                    logger.warning("未获取到二维码图片，请检查MCP服务状态")

                # 等待用户扫码确认
                logger.info("请扫码完成后输入 'y' 并按回车键确认...")
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input(">> ")
                )

                if user_input.strip().lower() != 'y':
                    logger.warning("输入非 'y'，登录流程取消")
                    return False

                # 检查登录状态
                logger.info("正在验证登录状态...")
                status = await self.mcp_client.check_login_status()

                if status.get("is_logged_in", False):
                    self.is_logged_in = True
                    logger.success("小红书登录成功！")
                    return True
                else:
                    logger.warning("登录失败，请重新扫码")
                    self.login_retry_count += 1
                    logger.info(f"重试次数: {self.login_retry_count}/{self.max_login_retries}")

            except Exception as e:
                logger.error(f"登录过程中出错: {e}")
                self.login_retry_count += 1
                logger.info(f"重试次数: {self.login_retry_count}/{self.max_login_retries}")

        # 达到最大重试次数
        raise RuntimeError(f"小红书登录失败，已达最大重试次数 ({self.max_login_retries})")

    @BaseAgent.tool(name="xhs_check_login", description="检查小红书登录状态")
    async def check_login_status(self) -> Dict[str, Any]:
        """
        检查小红书登录状态

        Returns:
            包含登录状态信息的字典
        """
        await self.ensure_connected()
        return await self.mcp_client.check_login_status()

    @BaseAgent.tool(name="xhs_get_qrcode", description="获取小红书登录二维码")
    async def get_login_qrcode(self) -> Dict[str, Any]:
        """
        获取小红书登录二维码

        Returns:
            包含二维码信息的字典
        """
        await self.ensure_connected()
        return await self.mcp_client.get_login_qrcode()

    @BaseAgent.tool(name="xhs_publish_content", description="发布小红书图文内容")
    async def publish_content(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        发布小红书图文内容

        Args:
            title: 标题（不超过20个中文字符）
            content: 正文内容（不超过1000字）
            images: 图片路径列表，支持本地路径或HTTP链接
            tags: 话题标签列表，可选

        Returns:
            发布结果信息字典

        Raises:
            RuntimeError: 发布失败时抛出
        """
        # 将相对路径转换为绝对路径，确保 MCP 服务（可能在不同工作目录运行）能找到图片
        absolute_images = []
        for image_path in images:
            # 如果是 HTTP/HTTPS 链接，直接使用
            if image_path.startswith(('http://', 'https://')):
                absolute_images.append(image_path)
            else:
                # 将相对路径转换为绝对路径
                abs_path = os.path.abspath(image_path)
                absolute_images.append(abs_path)
                logger.debug(f"图片路径转换: {image_path} -> {abs_path}")

        arguments = {
            "title": title,
            "content": content,
            "images": absolute_images,
        }
        if tags:
            arguments["tags"] = tags

        results = await self.mcp_client.call_tool("publish_content", arguments)

        # 解析结果
        publish_result = {"success": False, "message": "发布结果未知"}
        for result in results:
            if result["type"] == "text":
                text = result["content"]
                if "发布成功" in text or "success" in text.lower():
                    publish_result["success"] = True
                publish_result["message"] = text

        return publish_result

    @BaseAgent.tool(name="xhs_search_feeds", description="搜索小红书内容")
    async def search_feeds(
        self,
        keyword: str,
        limit: int = 10,
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索小红书内容

        Args:
            keyword: 搜索关键词
            limit: 结果数量限制，默认10
            filters: 筛选选项字典，可选

        Returns:
            搜索结果列表
        """
        arguments = {"keyword": keyword}
        if filters:
            arguments["filters"] = filters

        results = await self.mcp_client.call_tool("search_feeds", arguments)

        # 解析结果
        search_results = []
        for result in results:
            if result["type"] == "text":
                # 这里可以进一步解析文本结果为结构化数据
                search_results.append({"type": "text", "content": result["content"]})

        return search_results

    @BaseAgent.tool(name="xhs_list_feeds", description="获取小红书首页推荐列表")
    async def list_feeds(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取小红书首页推荐列表

        Args:
            limit: 结果数量限制，默认20

        Returns:
            推荐列表
        """

        results = await self.mcp_client.call_tool("list_feeds", {"limit": limit})

        # 解析结果
        feeds = []
        for result in results:
            if result["type"] == "text":
                feeds.append({"type": "text", "content": result["content"]})

        return feeds

    @BaseAgent.tool(name="xhs_post_comment", description="发表评论到小红书帖子")
    async def post_comment(
        self,
        feed_id: str,
        content: str,
        xsec_token: str
    ) -> Dict[str, Any]:
        """
        发表评论到小红书帖子

        Args:
            feed_id: 帖子ID
            content: 评论内容
            xsec_token: 访问令牌

        Returns:
            评论结果信息
        """
        arguments = {
            "feed_id": feed_id,
            "content": content,
            "xsec_token": xsec_token
        }

        results = await self.mcp_client.call_tool("post_comment_to_feed", arguments)

        comment_result = {"success": False, "message": "评论结果未知"}
        for result in results:
            if result["type"] == "text":
                text = result["content"]
                if "发表成功" in text or "success" in text.lower():
                    comment_result["success"] = True
                comment_result["message"] = text

        return comment_result

    @BaseAgent.tool(name="xhs_publish_video", description="发布小红书视频内容")
    async def publish_video(
        self,
        title: str,
        content: str,
        video: str,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        发布小红书视频内容

        Args:
            title: 标题（不超过20个中文字符）
            content: 正文内容（不超过1000字）
            video: 本地视频文件路径（相对路径或绝对路径）
            tags: 话题标签列表，可选

        Returns:
            发布结果信息字典

        Raises:
            RuntimeError: 发布失败时抛出
        """
        # 将相对路径转换为绝对路径，确保 MCP 服务（可能在不同工作目录运行）能找到视频
        if not video.startswith(('http://', 'https://')):
            # 如果是本地路径，转换为绝对路径
            absolute_video = os.path.abspath(video)
            logger.debug(f"视频路径转换: {video} -> {absolute_video}")
            video = absolute_video

        arguments = {
            "title": title,
            "content": content,
            "video": video,
        }
        if tags:
            arguments["tags"] = tags

        results = await self.mcp_client.call_tool("publish_with_video", arguments)

        # 解析结果
        publish_result = {"success": False, "message": "发布结果未知"}
        for result in results:
            if result["type"] == "text":
                text = result["content"]
                if "发布成功" in text or "success" in text.lower():
                    publish_result["success"] = True
                publish_result["message"] = text

        return publish_result

    @BaseAgent.tool(name="xhs_get_feed_detail", description="获取小红书笔记详情")
    async def get_feed_detail(
        self,
        feed_id: str,
        xsec_token: str
    ) -> Dict[str, Any]:
        """
        获取小红书笔记详情

        Args:
            feed_id: 笔记ID
            xsec_token: 访问令牌

        Returns:
            笔记详情信息字典
        """
        arguments = {
            "feed_id": feed_id,
            "xsec_token": xsec_token
        }

        results = await self.mcp_client.call_tool("get_feed_detail", arguments)

        # 解析结果
        detail_info = {"success": False, "data": {}, "message": "获取详情失败"}
        for result in results:
            if result["type"] == "text":
                # 这里可以进一步解析文本结果为结构化数据
                text = result["content"]
                if "笔记详情" in text or "成功" in text:
                    detail_info["success"] = True
                detail_info["message"] = text
                # 可以添加更复杂的解析逻辑

        return detail_info

    @BaseAgent.tool(name="xhs_user_profile", description="获取小红书用户主页信息")
    async def user_profile(
        self,
        user_id: str,
        xsec_token: str
    ) -> Dict[str, Any]:
        """
        获取小红书用户主页信息

        Args:
            user_id: 用户ID
            xsec_token: 访问令牌

        Returns:
            用户主页信息字典
        """

        arguments = {
            "user_id": user_id,
            "xsec_token": xsec_token
        }

        results = await self.mcp_client.call_tool("user_profile", arguments)

        # 解析结果
        profile_info = {"success": False, "data": {}, "message": "获取用户信息失败"}
        for result in results:
            if result["type"] == "text":
                text = result["content"]
                if "用户信息" in text or "成功" in text:
                    profile_info["success"] = True
                profile_info["message"] = text

        return profile_info

    @BaseAgent.tool(name="xhs_like_feed", description="点赞或取消点赞小红书笔记")
    async def like_feed(
        self,
        feed_id: str,
        xsec_token: str,
        unlike: bool = False
    ) -> Dict[str, Any]:
        """
        点赞或取消点赞小红书笔记

        Args:
            feed_id: 笔记ID
            xsec_token: 访问令牌
            unlike: 是否取消点赞，默认为False（点赞）

        Returns:
            操作结果信息字典
        """

        arguments = {
            "feed_id": feed_id,
            "xsec_token": xsec_token,
            "unlike": unlike
        }

        results = await self.mcp_client.call_tool("like_feed", arguments)

        # 解析结果
        like_result = {"success": False, "message": "操作失败"}
        for result in results:
            if result["type"] == "text":
                text = result["content"]
                if "成功" in text or "already" in text.lower():
                    like_result["success"] = True
                like_result["message"] = text

        return like_result

    @BaseAgent.tool(name="xhs_favorite_feed", description="收藏或取消收藏小红书笔记")
    async def favorite_feed(
        self,
        feed_id: str,
        xsec_token: str,
        unfavorite: bool = False
    ) -> Dict[str, Any]:
        """
        收藏或取消收藏小红书笔记

        Args:
            feed_id: 笔记ID
            xsec_token: 访问令牌
            unfavorite: 是否取消收藏，默认为False（收藏）

        Returns:
            操作结果信息字典
        """
        arguments = {
            "feed_id": feed_id,
            "xsec_token": xsec_token,
            "unfavorite": unfavorite
        }

        results = await self.mcp_client.call_tool("favorite_feed", arguments)

        # 解析结果
        favorite_result = {"success": False, "message": "操作失败"}
        for result in results:
            if result["type"] == "text":
                text = result["content"]
                if "成功" in text or "already" in text.lower():
                    favorite_result["success"] = True
                favorite_result["message"] = text

        return favorite_result

    @BaseAgent.tool(name="xhs_delete_cookies", description="删除cookies文件，重置登录状态")
    async def delete_cookies(self) -> Dict[str, Any]:
        """
        删除cookies文件，重置登录状态

        删除后需要重新登录小红书

        Returns:
            操作结果信息字典
        """
        await self.ensure_connected()

        results = await self.mcp_client.call_tool("delete_cookies", {})

        # 解析结果
        delete_result = {"success": False, "message": "操作失败"}
        for result in results:
            if result["type"] == "text":
                text = result["content"]
                if "成功" in text or "deleted" in text.lower():
                    delete_result["success"] = True
                delete_result["message"] = text

        # 重置登录状态
        if delete_result["success"]:
            self.is_logged_in = False
            self.login_retry_count = 0

        return delete_result

    @BaseAgent.tool(name="xhs_call_tool", description="通用MCP工具调用")
    async def call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        通用MCP工具调用

        用于调用未单独封装的MCP工具

        Args:
            tool_name: MCP工具名称
            arguments: 工具参数字典

        Returns:
            工具执行结果列表
        """
        await self.ensure_connected()
        return await self.mcp_client.call_tool(tool_name, arguments or {})

    @BaseAgent.tool(name="xhs_generate_content", description="使用LLM生成小红书帖子内容")
    async def generate_xhs_content(
        self,
        topic: str,
        style: str = None,
        target_audience: str = None,
        max_tags: int = 3,
        user_query: str = None,
        knowledge: str = None,
        previous_notes_title: Optional[List[str]] = None
    ) -> XHSContent:
        """
        使用LLM生成小红书帖子内容

        Args:
            topic: 帖子主题
            style: 内容风格，如"生活分享"、"美食教程"、"旅行日记"等
            target_audience: 目标受众，如"年轻人"、"宝妈"、"学生"等
            max_tags: 最多生成的话题标签数量
            previous_notes_title: 之前发布的笔记标题列表，用于避免内容重复

        Returns:
            XHSContent对象，包含生成的标题、内容、标签等

        Raises:
            RuntimeError: LLM生成失败时抛出
        """
        try:
            previous_notes_title = previous_notes_title or []
            # 使用LLM生成结构化内容
            content = await self.generate_with_prompt(
                template_name="xhs_content_generation",
                response_model=XHSContent,
                system_prompt="你是一个专业的小红书内容创作者，擅长创作吸引人的帖子内容。",
                topic=topic,
                style=style,
                target_audience=target_audience,
                max_tags=max_tags,
                user_query=user_query,
                knowledge=knowledge,
                previous_notes_title=previous_notes_title
            )

            # 验证生成的内容
            if not content.validate_content():
                logger.warning("生成的内容可能超出小红书限制，请人工检查")

            # 根据生成内容生成图片
            poster_data = {
                "title": content.title,
                "subtitle": content.subtitle,
                "content": content.content[:POSTER_WORD_COUNT],
                "note": 'defult'
            }
            image_path = await create_poster(data=poster_data, task_id='test2')
            content = content.__dict__
            content["image_path"] = image_path
            return content

        except Exception as e:
            raise RuntimeError(f"生成小红书内容失败: {e}")

    async def generate_comment(
        self,
        note_content: str,
        comments: List[Dict[str, Any]],
        tone: Optional[str] = None,
        is_reply: bool = True,
        target_comment_id: Optional[str] = None
    ) -> XHSComment:
        """
        根据笔记内容和现有评论生成小红书评论

        Args:
            note_content: 笔记正文内容
            comments: 现有评论列表，每个评论为字典格式，至少包含'content'字段
            tone: 期望的评论语气，如友好、专业、幽默、鼓励等（可选）
            is_reply: 是否为回复评论，默认为True（如果有现有评论则回复，无评论则置为False）
            target_comment_id: 回复的目标评论ID（如果是回复评论）

        Returns:
            XHSComment对象，包含生成的评论内容、语气等信息

        Raises:
            RuntimeError: LLM生成失败时抛出
        """
        # 如果评论列表为空，则不能是回复评论
        if not comments:
            is_reply = False
            target_comment_id = None
            logger.debug("评论列表为空，将生成普通评论（非回复）")

        try:
            # 使用LLM生成结构化评论
            comment = await self.generate_with_prompt(
                template_name="xhs_comment_generation",
                response_model=XHSComment,
                system_prompt="你是一个小红书社区运营专家，擅长生成自然、友好、有价值的评论。",
                note_content=note_content,
                comments=comments,
                tone=tone,
                is_reply=is_reply,
                target_comment_id=target_comment_id
            )

            # 验证生成的评论
            if not comment.validate_content():
                logger.warning("生成的评论可能超出小红书限制，请人工检查")

            logger.info(f"小红书评论生成成功: {comment.content[:50]}...")
            return comment

        except Exception as e:
            raise RuntimeError(f"生成小红书评论失败: {e}")

    async def get_own_notes(self, note_title, notes_num=1):
        """
        搜索自己发布过的某一篇笔记
        :return:
        """
        # 搜索自己
        # 用id和用户昵称搜索笔记
        notes_info = await self.search_feeds(keyword=str(self.user_name) + ' '+ str(note_title))
        # 获取user_info当中的第一个且nick_name和用户一致的笔记
        notes_content_list = []
        if notes_info:
            for i in range(notes_num):
                try:
                    type_text = notes_info[0]
                    if type_text.get('type') == 'text':
                        notes_content = type_text['content']
                        note_info = json.loads(notes_content)['feeds'][i]
                        xsecToken, id = note_info["xsecToken"], note_info["id"]
                        # 搜索该内容的用户信息
                        user_info_ori = await self.get_feed_detail(feed_id=id, xsec_token=xsecToken)
                        message = json.loads(user_info_ori['message'])
                        if message:
                            logger.debug(message)
                            notes_content_list.append(message)
                except Exception as e:
                    logger.warning(e)

                logger.info(f"共获取到{notes_num}个笔记")
            return notes_content_list
        logger.warning(f"未获取到有效笔记")
        return []



    async def interact_with_topic_notes(
        self,
        topic: str,
        interaction_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        搜索主题相关的笔记并进行互动（点赞、收藏、评论）
        
        Args:
            topic: 主题关键词（必填）
            interaction_count: 互动笔记数量，默认使用 self.interaction_note_count
            
        Returns:
            互动结果统计
        """
        if not topic:
            logger.warning("主题关键词为空，跳过主题笔记互动")
            return {"success": False, "message": "主题关键词为空", "interacted_count": 0}
        
        interaction_count = interaction_count or self.interaction_note_count
        interaction_count = max(1, min(5, interaction_count))
        
        logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
            f"开始搜索主题相关笔记进行互动: 主题={topic}, 数量={interaction_count}"
        )
        
        try:
            # 1. 搜索主题相关笔记
            search_results = await self.search_feeds(keyword=topic, limit=interaction_count)
            
            if not search_results:
                logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).warning(
                    f"未搜索到主题相关的笔记: {topic}"
                )
                return {"success": False, "message": "未搜索到相关笔记", "interacted_count": 0}
            
            # 2. 解析搜索结果，获取笔记详情
            interacted_count = 0
            for i, result in enumerate(search_results):
                try:
                    if result.get('type') != 'text':
                        continue
                    
                    # 解析搜索结果（假设返回的是JSON字符串）
                    content = result.get('content', '')
                    try:
                        feeds_data = json.loads(content) if isinstance(content, str) else content
                        feeds = feeds_data.get('feeds', [])
                    except (json.JSONDecodeError, AttributeError):
                        logger.warning(f"无法解析搜索结果: {content[:100]}")
                        continue
                    
                    if not feeds:
                        continue
                    
                    # 对每条笔记进行互动
                    for feed in feeds[:interaction_count - interacted_count]:
                        if interacted_count >= interaction_count:
                            break
                        
                        try:
                            feed_id = feed.get('id')
                            xsec_token = feed.get('xsecToken')
                            
                            if not feed_id or not xsec_token:
                                logger.warning(f"笔记缺少必要字段: id={feed_id}, xsecToken={xsec_token}")
                                continue
                            
                            # 获取笔记详情（用于生成评论）
                            feed_detail = await self.get_feed_detail(feed_id=feed_id, xsec_token=xsec_token)
                            note_content = ""
                            comments = []
                            
                            try:
                                detail_message = feed_detail.get('message', '')
                                # 检查detail_message是否有效
                                if detail_message and isinstance(detail_message, str) and detail_message.strip():
                                    try:
                                        detail_data = json.loads(detail_message)
                                    except json.JSONDecodeError:
                                        # 如果已经是字典，直接使用
                                        detail_data = detail_message if isinstance(detail_message, dict) else {}
                                elif isinstance(detail_message, dict):
                                    detail_data = detail_message
                                else:
                                    detail_data = {}
                                
                                if detail_data:
                                    note_data = detail_data.get('data', {}).get('note', {})
                                    note_content = note_data.get('desc', '')
                                    comments_data = detail_data.get('data', {}).get('comments', {})
                                    comments = comments_data.get('list', [])
                            except Exception as e:
                                logger.debug(f"解析笔记详情失败: {e}, feed_detail类型: {type(feed_detail)}, message类型: {type(feed_detail.get('message', ''))}")
                            
                            # 执行互动操作：点赞 → 收藏 → 评论
                            # 点赞
                            await asyncio.sleep(random.randint(2, 5))
                            like_result = await self.like_feed(feed_id=feed_id, xsec_token=xsec_token, unlike=False)
                            if like_result.get('success'):
                                logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
                                    f"点赞笔记成功: feed_id={feed_id}"
                                )
                            
                            # 收藏
                            await asyncio.sleep(random.randint(2, 5))
                            favorite_result = await self.favorite_feed(feed_id=feed_id, xsec_token=xsec_token, unfavorite=False)
                            if favorite_result.get('success'):
                                logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
                                    f"收藏笔记成功: feed_id={feed_id}"
                                )
                            
                            # 评论（使用现有的generate_comment方法生成评论）
                            if note_content:
                                await asyncio.sleep(random.randint(3, 8))
                                try:
                                    comment_obj = await self.generate_comment(
                                        note_content=note_content,
                                        comments=comments,
                                        tone="友好",
                                        is_reply=False
                                    )
                                    comment_result = await self.post_comment(
                                        feed_id=feed_id,
                                        content=comment_obj.content,
                                        xsec_token=xsec_token
                                    )
                                    if comment_result.get('success'):
                                        logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
                                            f"评论笔记成功: feed_id={feed_id}, 评论={comment_obj.content[:50]}..."
                                        )
                                except Exception as e:
                                    logger.warning(f"生成或发表评论失败: {e}")
                            
                            interacted_count += 1
                            
                            # 每条笔记之间随机间隔5-20秒
                            if interacted_count < interaction_count:
                                await asyncio.sleep(random.randint(5, 20))
                        
                        except Exception as e:
                            logger.warning(f"互动笔记失败: {e}")
                            continue
                    
                    if interacted_count >= interaction_count:
                        break
                
                except Exception as e:
                    logger.warning(f"处理搜索结果失败: {e}")
                    continue
            
            logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
                f"主题笔记互动完成: 成功互动 {interacted_count} 条笔记"
            )
            
            return {
                "success": True,
                "message": f"成功互动 {interacted_count} 条笔记",
                "interacted_count": interacted_count
            }
        
        except Exception as e:
            logger.error(f"主题笔记互动失败: {e}", exc_info=True)
            return {"success": False, "message": str(e), "interacted_count": 0}

    async def get_n_last_notes_title(self, n=3):
        """
        根据user_id，从notes中获取历史最近n个笔记记录的title字段，并以list输出

        Args:
            n: 需要获取的笔记数量，默认为3

        Returns:
            list: 包含最近n个笔记标题的列表，按时间从新到旧排序
        """
        # 构建笔记文件路径
        notes_file = get_user_notes_file_path(self.user_id)

        # 检查文件是否存在
        if not os.path.exists(notes_file):
            logger.warning(f"笔记文件不存在: {notes_file}")
            return []

        notes = []
        try:
            with open(notes_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        note_data = json.loads(line)
                        # 确保有create_time字段，用于排序
                        if 'create_time' in note_data and 'title' in note_data:
                            notes.append(note_data)
                        else:
                            logger.debug(f"笔记数据缺少必要字段: {note_data}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析JSON行失败: {line}, 错误: {e}")
                        continue

            # 按create_time降序排序（最新的在前）
            # 使用datetime对象进行精确排序，如果解析失败则回退到字符串排序
            def get_sort_key(note):
                create_time_str = note.get('create_time', '')
                try:
                    # 尝试解析为datetime对象
                    return datetime.strptime(create_time_str, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    # 解析失败，使用原始字符串
                    return create_time_str

            notes.sort(key=get_sort_key, reverse=True)

            # 获取前n个笔记的title
            titles = [note['title'] for note in notes[:n] if 'title' in note]
            logger.info(f"成功获取用户 {self.user_id} 最近 {len(titles)} 个笔记标题")
            return titles

        except Exception as e:
            logger.error(f"读取笔记文件失败: {e}")
            return []

    async def comment_own_notes(self) -> None:
        """
        评论自己的历史笔记（抽取自原 run 方法）
        """
        previous_notes_title = await self.get_n_last_notes_title(self.comment_note_nums)
        logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
            f"获取到的前{self.comment_note_nums}篇笔记标题: {previous_notes_title}"
        )
        
        # 获取自己过去n篇笔记的内容和评论，并在评论区补充评论
        for note_title in previous_notes_title:
            try:
                await asyncio.sleep(random.randint(5, 20))
                notes_info = await self.get_own_notes(note_title)
                # 获取评论信息
                note_info = notes_info[0]
                comments = note_info['data']['comments']['list']
                note_content = note_info['data']['note']['desc']
                note_id, xsecToken = note_info['data']['note']['noteId'], note_info['data']['note']['xsecToken']
                logger.debug(f"获取到的id和token：{note_id}, {xsecToken}")
                # 评论该笔记
                logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
                    f"开始评论笔记: {note_title}"
                )
                new_comments_obj = await self.generate_comment(note_content=note_content, comments=comments)
                new_comments = new_comments_obj.content

                await self.post_comment(feed_id=note_id, content=new_comments, xsec_token=xsecToken)
                logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
                    f"发表评论{new_comments[:50]}成功"
                )
            except Exception as e:
                logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).warning(
                    f"评论历史笔记{note_title}失败：{e}"
                )
                continue

    async def publish_new_note(self) -> None:
        """
        发布新笔记（抽取自原 run 方法）
        """
        # 获取历史笔记标题（用于避免重复），默认获取最近3个
        previous_notes_title = await self.get_n_last_notes_title(3)
        
        # 根据知识库，发布一篇笔记
        ## 获取知识库中的知识生成笔记内容
        source_file_path = get_user_source_file_path(self.user_id)
        with open(source_file_path, 'r') as f:
            knowledge_text = f.read()
        
        res = await self.generate_xhs_content(
            topic=self.user_topic,
            style=self.user_style,
            target_audience=self.user_target_audience,
            max_tags=3,
            knowledge=knowledge_text,
            user_query=self.user_query,
            previous_notes_title=previous_notes_title
        )
        logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
            f"生成的小红书内容: {res}"
        )

        ## 生成图片
        generate_image_path = await create_poster(
            data=res, 
            task_id=self.task_id, 
            output_dir=get_user_images_path(self.user_id)
        )
        logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
            f"根据生成内容生成小红书海报图片：{generate_image_path}"
        )

        ## 发表内容
        await self.publish_content(
            title=res.get('title'),
            content=res.get('content'),
            tags=res.get('tags'),
            images=[generate_image_path]
        )
        logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
            f"小红书笔记发布完成"
        )

        ## 保存笔记的title
        notes_file_path = get_user_notes_file_path(self.user_id)
        with open(notes_file_path, 'a') as f:
            res['create_time'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
            res['task_id'] = self.task_id
            f.write(json.dumps(res, ensure_ascii=False) + '\n')
        logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
            f"账号{self.user_id}, 任务{self.task_id}完成记录"
        )

    async def run(self) -> Any:
        """
        小红书智能体主执行逻辑（支持模式切换）

        实现BaseAgent的抽象方法，根据任务模式执行不同的操作：
        - 标准模式：互动主题笔记 → 评论自己的历史笔记 → 发布新笔记
        - 互动模式：互动主题笔记 → 评论自己的历史笔记
        - 发布模式：发布新笔记

        Returns:
            执行结果，类型取决于具体任务

        Raises:
            RuntimeError: 执行失败时抛出
        """
        try:
            logger.info("小红书智能体开始执行...")

            # 1. 建立MCP连接
            await self.ensure_connected()

            # 2. 确保登录状态
            # logged_in = await self.ensure_logged_in()
            # if not logged_in:
            #     return {"success": False, "message": "小红书登录失败"}

            # 3. 根据模式执行不同逻辑
            from app.data.constants import TaskMode
            
            if self.mode == TaskMode.STANDARD:
                # 标准模式：互动 + 发布
                logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
                    "执行标准模式：互动主题笔记 → 评论历史笔记 → 发布新笔记"
                )
                
                # 1. 搜索主题相关笔记并互动
                if self.user_topic:
                    await self.interact_with_topic_notes(self.user_topic)
                else:
                    logger.warning("任务主题为空，跳过主题笔记互动")
                
                # 2. 评论自己的历史笔记
                await self.comment_own_notes()
                
                # 3. 发布新笔记
                await self.publish_new_note()
                
            elif self.mode == TaskMode.INTERACTION:
                # 互动模式：仅互动
                logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
                    "执行互动模式：互动主题笔记 → 评论历史笔记"
                )
                
                # 1. 搜索主题相关笔记并互动
                if self.user_topic:
                    await self.interact_with_topic_notes(self.user_topic)
                else:
                    logger.warning("任务主题为空，跳过主题笔记互动")
                
                # 2. 评论自己的历史笔记
                await self.comment_own_notes()
                
            elif self.mode == TaskMode.PUBLISH:
                # 发布模式：仅发布
                logger.bind(task_id=self.task_id, bindtype=LogBindType.TASK_LOG).info(
                    "执行发布模式：发布新笔记"
                )
                
                # 1. 发布新笔记
                await self.publish_new_note()
                
            else:
                logger.warning(f"未知的任务模式: {self.mode}，使用标准模式")
                await self.comment_own_notes()
                await self.publish_new_note()

            logger.info("小红书智能体执行完成")
            return {"success": True, "message": "小红书智能体执行成功"}

        except Exception as e:
            logger.error(f"小红书智能体执行失败: {e}")
            raise RuntimeError(f"小红书智能体执行失败: {e}")
        finally:
            # 清理MCP连接资源
            if hasattr(self, 'mcp_client') and self.mcp_client:
                try:
                    await self.mcp_client.close()
                except Exception as close_error:
                    logger.debug(f"关闭MCP连接时发生错误（可忽略）: {close_error}")
