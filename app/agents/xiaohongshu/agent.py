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
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

# MCP协议相关导入
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("警告：mcp库未安装，XiaohongshuAgent功能受限")

# Pydantic模型导入
from pydantic import BaseModel, Field

# 项目内部导入
from app.agents.base import BaseAgent, BaseAgent as BaseAgentTool
from app.core.context import Context
from app.core.llm import LLMService
from app.core.prompts import PromptEngine, prompt_engine


class MCPClient:
    """
    MCP客户端封装类 - 负责与小红书MCP服务通信

    封装MCP协议细节，提供简洁的API供Agent调用。
    基于test/client2.py中的最佳实践实现。
    """

    def __init__(self, server_url: str = "http://localhost:18060/mcp"):
        """
        初始化MCP客户端

        Args:
            server_url: MCP服务器URL，默认为本地18060端口的/mcp端点
        """
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self._transport_context = None  # streamablehttp_client上下文管理器
        self._transport = None  # (read_stream, write_stream, get_session_id)三元组
        self.tools_info: Dict[str, Dict] = {}

    async def connect(self) -> None:
        """
        连接到MCP服务器

        建立传输层连接，执行握手协议，获取工具列表。
        必须在调用任何工具前执行。

        Raises:
            ConnectionError: 连接失败时抛出
        """
        if not MCP_AVAILABLE:
            raise ImportError("mcp库未安装，无法连接MCP服务器")

        try:
            # 1. 创建传输层上下文管理器
            self._transport_context = streamablehttp_client(self.server_url)

            # 2. 进入传输层上下文，获取流
            self._transport = await self._transport_context.__aenter__()
            read_stream, write_stream, get_session_id = self._transport

            # 3. 创建MCP协议会话 (Client Session)
            self.session = await ClientSession(read_stream, write_stream).__aenter__()

            # 4. 执行握手协议 (Handshake) - 关键步骤！
            init_result = await self.session.initialize()
            print(f"✅ MCP连接成功，服务器版本: {init_result.protocolVersion}")

            # 5. 获取工具列表 (Discovery)
            tools_list = await self.session.list_tools()
            self.tools_info = {
                tool.name: {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in tools_list.tools
            }
            print(f"✅ 发现 {len(self.tools_info)} 个MCP工具")

        except Exception as e:
            # 清理资源
            await self._close_resources()
            raise ConnectionError(f"连接MCP服务器失败: {e}")

    async def _close_resources(self):
        """清理MCP资源"""
        try:
            # 1. 关闭MCP会话
            if self.session:
                await self.session.__aexit__(None, None, None)
                self.session = None

            # 2. 关闭传输层上下文管理器
            if self._transport_context:
                await self._transport_context.__aexit__(None, None, None)
                self._transport_context = None
                self._transport = None  # 三元组引用

        except Exception:
            # 忽略关闭过程中的错误
            pass

    async def close(self):
        """关闭MCP连接"""
        await self._close_resources()
        print("✅ MCP连接已关闭")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        调用MCP工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数字典

        Returns:
            工具执行结果列表，每个元素是包含类型和内容的字典

        Raises:
            ValueError: 工具不存在或未连接时抛出
            RuntimeError: 工具调用失败时抛出
        """
        if not self.session:
            raise ValueError("MCP客户端未连接，请先调用connect()方法")

        if tool_name not in self.tools_info:
            available_tools = list(self.tools_info.keys())
            raise ValueError(f"工具 '{tool_name}' 不存在。可用工具: {available_tools}")

        try:
            result = await self.session.call_tool(tool_name, arguments or {})

            # 将结果转换为字典列表
            results = []
            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        results.append({"type": "text", "content": content.text})
                    elif hasattr(content, 'data'):
                        # 处理二进制数据（如图片）
                        results.append({"type": "binary", "content": content.data})
            return results

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            error_msg = str(e) if str(e) else "空错误消息"
            raise RuntimeError(f"调用工具 '{tool_name}' 失败: {error_msg}\n详细错误:\n{error_details}")

    async def check_login_status(self) -> Dict[str, Any]:
        """
        检查小红书登录状态

        Returns:
            包含登录状态信息的字典
        """
        results = await self.call_tool("check_login_status", {})

        # 解析结果
        status_info = {"is_logged_in": False, "message": "未知状态"}
        for result in results:
            if result["type"] == "text":
                text = result["content"]
                if "已登录" in text or "登录成功" in text:
                    status_info["is_logged_in"] = True
                    status_info["message"] = text
                elif "未登录" in text or "需要登录" in text:
                    status_info["is_logged_in"] = False
                    status_info["message"] = text

        return status_info

    async def get_login_qrcode(self) -> Dict[str, Any]:
        """
        获取登录二维码

        Returns:
            包含二维码信息的字典，包括base64编码的图片数据和超时时间
        """
        results = await self.call_tool("get_login_qrcode", {})

        qrcode_info = {"base64_image": "", "timeout": 180, "message": ""}
        for result in results:
            if result["type"] == "text":
                # 解析文本结果中的信息
                text = result["content"]
                qrcode_info["message"] = text
            elif result["type"] == "binary":
                # 二进制数据为base64编码的图片
                qrcode_info["base64_image"] = result["content"]

        return qrcode_info

    def save_qrcode_image(self, base64_data: str, filename: str = "login_qrcode.jpg") -> str:
        """
        保存二维码图片到文件

        Args:
            base64_data: base64编码的图片数据
            filename: 保存的文件名

        Returns:
            保存的文件路径

        Raises:
            ValueError: base64数据无效时抛出
        """
        if not base64_data:
            raise ValueError("base64图片数据为空")

        # 确保目录存在
        qrcode_dir = Path.cwd() / "qrcodes"
        qrcode_dir.mkdir(exist_ok=True)

        # 保存图片
        filepath = qrcode_dir / filename
        try:
            # 解码base64数据
            image_data = base64.b64decode(base64_data)
            with open(filepath, "wb") as f:
                f.write(image_data)
            return str(filepath)
        except Exception as e:
            raise ValueError(f"保存二维码图片失败: {e}")


class XHSContent(BaseModel):
    """
    小红书内容生成模型

    用于LLM生成小红书帖子内容的结构化输出
    """
    title: str = Field(description="帖子标题，不超过20个中文字符")
    content: str = Field(description="帖子正文内容，不超过1000字")
    tags: List[str] = Field(description="话题标签列表，最多5个", default_factory=list)
    image_suggestions: List[str] = Field(description="图片内容建议描述", default_factory=list)

    def validate_content(self) -> bool:
        """验证内容是否符合小红书要求"""
        # 简单验证：标题长度不超过20个字符
        if len(self.title) > 20:
            return False
        # 内容长度不超过1000个字符
        if len(self.content) > 1000:
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
        mcp_server_url: str = "http://localhost:18060/mcp"
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

        # 登录状态
        self.is_logged_in = False
        self.login_retry_count = 0
        self.max_login_retries = 3

        print(f"✅ 小红书智能体初始化完成，MCP服务器: {mcp_server_url}")

    async def ensure_connected(self) -> None:
        """
        确保MCP连接已建立

        如果未连接，则建立连接；如果已连接，则跳过。

        Raises:
            ConnectionError: 连接失败时抛出
        """
        if not self.is_connected:
            try:
                await self.mcp_client.connect()
                self.is_connected = True
                print("✅ MCP连接已建立")
            except Exception as e:
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
                print("✅ 小红书已登录")
                return True
        except Exception as e:
            print(f"⚠️ 检查登录状态失败: {e}")

        # 未登录，开始登录流程
        print("🔑 小红书未登录，开始登录流程...")

        while self.login_retry_count < self.max_login_retries:
            try:
                # 获取登录二维码
                print("📱 正在获取登录二维码...")
                qrcode_info = await self.mcp_client.get_login_qrcode()

                # 保存二维码图片
                if qrcode_info.get("base64_image"):
                    filepath = self.mcp_client.save_qrcode_image(qrcode_info["base64_image"])
                    print(f"📷 二维码已保存至: {filepath}")
                    print("📱 请使用小红书App扫描二维码登录")
                else:
                    print("⚠️ 未获取到二维码图片，请检查MCP服务状态")

                # 等待用户扫码确认
                print("⏳ 请扫码完成后输入 'y' 并按回车键确认...")
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input(">> ")
                )

                if user_input.strip().lower() != 'y':
                    print("❌ 输入非 'y'，登录流程取消")
                    return False

                # 检查登录状态
                print("🔍 正在验证登录状态...")
                status = await self.mcp_client.check_login_status()

                if status.get("is_logged_in", False):
                    self.is_logged_in = True
                    print("✅ 小红书登录成功！")
                    return True
                else:
                    print("❌ 登录失败，请重新扫码")
                    self.login_retry_count += 1
                    print(f"🔄 重试次数: {self.login_retry_count}/{self.max_login_retries}")

            except Exception as e:
                print(f"❌ 登录过程中出错: {e}")
                self.login_retry_count += 1
                print(f"🔄 重试次数: {self.login_retry_count}/{self.max_login_retries}")

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
        await self.ensure_connected()
        await self.ensure_logged_in()

        arguments = {
            "title": title,
            "content": content,
            "images": images,
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
        await self.ensure_connected()
        await self.ensure_logged_in()

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
        await self.ensure_connected()
        await self.ensure_logged_in()

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
        await self.ensure_connected()
        await self.ensure_logged_in()

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
            video: 本地视频文件绝对路径
            tags: 话题标签列表，可选

        Returns:
            发布结果信息字典

        Raises:
            RuntimeError: 发布失败时抛出
        """
        await self.ensure_connected()
        await self.ensure_logged_in()

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
        await self.ensure_connected()
        await self.ensure_logged_in()

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
        await self.ensure_connected()
        await self.ensure_logged_in()

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
        await self.ensure_connected()
        await self.ensure_logged_in()

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
        await self.ensure_connected()
        await self.ensure_logged_in()

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
        style: str = "生活分享",
        target_audience: str = "年轻人",
        max_tags: int = 3
    ) -> XHSContent:
        """
        使用LLM生成小红书帖子内容

        Args:
            topic: 帖子主题
            style: 内容风格，如"生活分享"、"美食教程"、"旅行日记"等
            target_audience: 目标受众，如"年轻人"、"宝妈"、"学生"等
            max_tags: 最多生成的话题标签数量

        Returns:
            XHSContent对象，包含生成的标题、内容、标签等

        Raises:
            RuntimeError: LLM生成失败时抛出
        """
        try:
            # 使用LLM生成结构化内容
            content = await self.generate_with_prompt(
                template_name="xhs_content_generation",
                response_model=XHSContent,
                system_prompt="你是一个专业的小红书内容创作者，擅长创作吸引人的帖子内容。",
                topic=topic,
                style=style,
                target_audience=target_audience,
                max_tags=max_tags
            )

            # 验证生成的内容
            if not content.validate_content():
                print("⚠️ 生成的内容可能超出小红书限制，请人工检查")

            return content

        except Exception as e:
            raise RuntimeError(f"生成小红书内容失败: {e}")
    async def get_own_notes(self):
        """
        获取该账号自己的笔记信息
        :return:
        """
        # 搜索自己的名称

    async def run(self) -> Any:
        """
        小红书智能体主执行逻辑

        实现BaseAgent的抽象方法，定义智能体的主要行为：
        1. 建立MCP连接
        2. 确保登录状态
        3. 根据上下文中的任务执行相应操作
        4. 返回执行结果

        Returns:
            执行结果，类型取决于具体任务

        Raises:
            RuntimeError: 执行失败时抛出
        """
        try:
            print("🚀 小红书智能体开始执行...")

            # 1. 建立MCP连接
            await self.ensure_connected()

            # 2. 确保登录状态
            logged_in = await self.ensure_logged_in()
            if not logged_in:
                return {"success": False, "message": "小红书登录失败"}
            # TO DO: 构建基于LLM的自动运维流程
            # 按照固定模式完成小红书运维任务
            # 检查用户信息，获取用户主页信息
            user_info = self.user_profile()
            # 3. 检查上下文中的任务
            # 这里可以根据context.blackboard中的任务信息执行相应操作
            # 例如：发布内容、搜索、评论等

            print("✅ 小红书智能体执行完成")
            return {"success": True, "message": "小红书智能体执行成功"}

        except Exception as e:
            print(f"❌ 小红书智能体执行失败: {e}")
            raise RuntimeError(f"小红书智能体执行失败: {e}")