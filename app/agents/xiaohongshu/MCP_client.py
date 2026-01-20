import asyncio
import base64

from typing import Any, Dict, List, Optional, Union
from pathlib import Path

# 日志配置导入 - 使用统一的日志管理模块
from app.core.logger import logger


# MCP协议相关导入
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    import httpx
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("mcp库未安装，XiaohongshuAgent功能受限")
    httpx = None


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
            # 增加超时时间：timeout=60秒（连接超时），sse_read_timeout=600秒（读取超时）
            # 使用自定义的 httpx 客户端工厂，设置 limits 和 trust_env=False 以解决连接问题
            def create_http_client(**kwargs):
                """创建自定义的 httpx 客户端，解决本地连接问题"""
                kwargs.setdefault('limits', httpx.Limits(max_connections=10, max_keepalive_connections=5))
                kwargs.setdefault('trust_env', False)
                return httpx.AsyncClient(**kwargs)
            
            logger.debug(f"正在创建MCP传输层连接: {self.server_url}")
            self._transport_context = streamablehttp_client(
                self.server_url,
                timeout=60.0,
                sse_read_timeout=600.0,
                httpx_client_factory=create_http_client
            )

            # 2. 进入传输层上下文，获取流
            logger.debug("正在进入传输层上下文...")
            self._transport = await self._transport_context.__aenter__()
            read_stream, write_stream, get_session_id = self._transport
            logger.debug("传输层上下文已建立")

            # 3. 创建MCP协议会话 (Client Session)
            logger.debug("正在创建MCP协议会话...")
            self.session = await ClientSession(read_stream, write_stream).__aenter__()
            logger.debug("MCP协议会话已创建")

            # 4. 执行握手协议 (Handshake) - 关键步骤！
            logger.debug("正在执行MCP初始化握手...")
            init_result = await self.session.initialize()
            logger.info(f"MCP连接成功，服务器版本: {init_result.protocolVersion}")

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
            logger.info(f"发现 {len(self.tools_info)} 个MCP工具")

        except asyncio.CancelledError as e:
            # 如果被取消，先清理资源，然后重新抛出
            logger.error(f"MCP连接被取消: {e}")
            await self._close_resources()
            raise
        except Exception as e:
            # 清理资源
            logger.error(f"连接MCP服务器失败: {e}", exc_info=True)
            await self._close_resources()
            raise ConnectionError(f"连接MCP服务器失败: {e}")

    async def _close_resources(self):
        """清理MCP资源"""
        try:
            # 1. 关闭MCP会话
            if self.session:
                try:
                    await self.session.__aexit__(None, None, None)
                except asyncio.CancelledError:
                    # 如果会话关闭被取消，记录日志但不影响
                    logger.debug("MCP会话关闭被取消（可能是请求超时），忽略此错误")
                self.session = None

            # 2. 关闭传输层上下文管理器
            if self._transport_context:
                try:
                    await self._transport_context.__aexit__(None, None, None)
                except asyncio.CancelledError:
                    # 如果传输层关闭被取消，记录日志但不影响
                    logger.debug("MCP传输层关闭被取消（可能是请求超时），忽略此错误")
                self._transport_context = None
                self._transport = None  # 三元组引用

        except asyncio.CancelledError:
            # 如果整个关闭过程被取消，记录日志但不影响
            logger.debug("MCP资源关闭过程被取消（可能是请求超时），忽略此错误")
        except Exception as e:
            # 忽略关闭过程中的其他错误
            logger.debug(f"关闭MCP资源时发生错误（可忽略）: {e}")

    async def close(self):
        """关闭MCP连接"""
        await self._close_resources()
        logger.info("MCP连接已关闭")

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
                    # 检查是否是 ImageContent 类型（优先检查，因为 ImageContent 可能也有 text 属性）
                    if hasattr(content, 'type') and getattr(content, 'type', None) == 'image':
                        # ImageContent: data 字段是 base64 编码的字符串
                        if hasattr(content, 'data'):
                            data = content.data
                            # ImageContent 的 data 已经是 base64 字符串，不需要再次编码
                            results.append({"type": "binary", "content": data})
                            logger.debug(f"处理 ImageContent，data 长度: {len(data) if data else 0}")
                        else:
                            logger.warning("ImageContent 缺少 data 字段")
                    elif hasattr(content, 'text'):
                        # TextContent
                        results.append({"type": "text", "content": content.text})
                    elif hasattr(content, 'data'):
                        # 其他类型的二进制数据
                        data = content.data
                        if isinstance(data, bytes):
                            # 如果是二进制数据，编码为 base64 字符串
                            import base64
                            data = base64.b64encode(data).decode('utf-8')
                        results.append({"type": "binary", "content": data})
                    else:
                        # 未知类型，尝试转换为字符串
                        logger.warning(f"未知的 content 类型: {type(content)}, 属性: {dir(content)}")
                        results.append({"type": "text", "content": str(content)})
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
        # 确保已连接
        if not self.session:
            raise ValueError("MCP客户端未连接，请先调用connect()方法")
        
        results = await self.call_tool("get_login_qrcode", {})

        qrcode_info = {"base64_image": "", "timeout": 180, "message": "", "qrcode_url": ""}
        
        # 调试日志：记录返回的结果
        logger.debug(f"get_login_qrcode 返回结果数量: {len(results)}")
        for i, result in enumerate(results):
            logger.debug(f"结果 {i}: type={result.get('type')}, content长度={len(str(result.get('content', '')))}")
        
        for result in results:
            if result["type"] == "text":
                # 解析文本结果中的信息
                text = result["content"]
                qrcode_info["message"] = text
                logger.debug(f"获取到文本消息: {text[:100]}...")  # 只记录前100个字符
            elif result["type"] == "binary":
                # 二进制数据为base64编码的图片
                base64_data = result["content"]
                if base64_data:
                    qrcode_info["base64_image"] = base64_data
                    qrcode_info["qrcode_url"] = f"data:image/png;base64,{base64_data}"
                    logger.debug(f"获取到二维码图片，base64长度: {len(base64_data)}")
                else:
                    logger.warning("二进制数据为空")

        if not qrcode_info["base64_image"]:
            logger.warning(f"未获取到二维码图片，返回结果: {results}")

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