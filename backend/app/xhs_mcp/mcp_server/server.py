"""
小红书 MCP 服务器

基于 MCP 协议提供小红书操作工具。
"""

import asyncio
import logging
from typing import Dict, Any, List

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from app.xhs_mcp.browser.pool import BrowserPool
from app.xhs_mcp.config.fingerprint_manager import FingerprintManager
from app.xhs_mcp.services.xhs_service import XHSService
from app.xhs_mcp.core.models import BrowserProfile, XHSAccount


class XHSMCPServer:
    """小红书 MCP 服务器"""

    def __init__(self):
        self.server = Server("xhs-mcp")
        self.browser_pool = BrowserPool(max_instances=10)
        self.fingerprint_manager = FingerprintManager()
        self.xhs_service = XHSService(self.browser_pool)

        self.logger = logging.getLogger(__name__)

        # 注册工具
        self._register_tools()

    def _register_tools(self):
        """注册 MCP 工具"""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """列出所有可用工具"""
            return [
                types.Tool(
                    name="create_browser_instance",
                    description="创建新的浏览器实例",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "profile_name": {
                                "type": "string",
                                "description": "浏览器配置名称"
                            },
                            "fingerprint_name": {
                                "type": "string",
                                "description": "指纹配置名称 (windows_chrome, macos_chrome, windows_edge, macos_safari)"
                            },
                            "headless": {
                                "type": "boolean",
                                "description": "是否无头模式",
                                "default": False
                            }
                        },
                        "required": ["profile_name", "fingerprint_name"]
                    }
                ),
                types.Tool(
                    name="list_browser_instances",
                    description="列出所有浏览器实例",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="xhs_login",
                    description="小红书扫码登录",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            }
                        },
                        "required": ["instance_id"]
                    }
                ),
                types.Tool(
                    name="xhs_publish_note",
                    description="发布小红书图文笔记",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            },
                            "content": {
                                "type": "string",
                                "description": "笔记内容"
                            },
                            "images": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "图片路径列表"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "标签列表"
                            }
                        },
                        "required": ["instance_id", "content"]
                    }
                ),
                types.Tool(
                    name="xhs_search",
                    description="小红书搜索",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            },
                            "keyword": {
                                "type": "string",
                                "description": "搜索关键词"
                            },
                            "limit": {
                                "type": "number",
                                "description": "结果数量限制",
                                "default": 10
                            }
                        },
                        "required": ["instance_id", "keyword"]
                    }
                ),
                types.Tool(
                    name="pause_browser_instance",
                    description="暂停浏览器实例",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            }
                        },
                        "required": ["instance_id"]
                    }
                ),
                types.Tool(
                    name="resume_browser_instance",
                    description="恢复浏览器实例",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            }
                        },
                        "required": ["instance_id"]
                    }
                ),
                types.Tool(
                    name="stop_browser_instance",
                    description="停止浏览器实例",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            }
                        },
                        "required": ["instance_id"]
                    }
                ),
                types.Tool(
                    name="list_fingerprints",
                    description="列出所有可用的指纹配置",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="xhs_post_comment",
                    description="发表评论到指定笔记",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            },
                            "feed_id": {
                                "type": "string",
                                "description": "笔记ID"
                            },
                            "content": {
                                "type": "string",
                                "description": "评论内容"
                            }
                        },
                        "required": ["instance_id", "feed_id", "content"]
                    }
                ),
                types.Tool(
                    name="xhs_like_feed",
                    description="点赞指定笔记",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            },
                            "feed_id": {
                                "type": "string",
                                "description": "笔记ID"
                            },
                            "unlike": {
                                "type": "boolean",
                                "description": "是否取消点赞",
                                "default": false
                            }
                        },
                        "required": ["instance_id", "feed_id"]
                    }
                ),
                types.Tool(
                    name="xhs_favorite_feed",
                    description="收藏指定笔记",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            },
                            "feed_id": {
                                "type": "string",
                                "description": "笔记ID"
                            },
                            "unfavorite": {
                                "type": "boolean",
                                "description": "是否取消收藏",
                                "default": false
                            }
                        },
                        "required": ["instance_id", "feed_id"]
                    }
                ),
                types.Tool(
                    name="xhs_list_feeds",
                    description="获取 Feed 列表",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_id": {
                                "type": "string",
                                "description": "浏览器实例ID"
                            },
                            "limit": {
                                "type": "number",
                                "description": "结果数量限制",
                                "default": 20
                            }
                        },
                        "required": ["instance_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str,
            arguments: dict[str, Any] | None
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """处理工具调用"""
            self.logger.info(f"调用工具: {name}, 参数: {arguments}")

            try:
                if name == "create_browser_instance":
                    return await self._create_browser_instance(arguments)
                elif name == "list_browser_instances":
                    return await self._list_browser_instances()
                elif name == "xhs_login":
                    return await self._xhs_login(arguments)
                elif name == "xhs_publish_note":
                    return await self._xhs_publish_note(arguments)
                elif name == "xhs_search":
                    return await self._xhs_search(arguments)
                elif name == "pause_browser_instance":
                    return await self._pause_browser_instance(arguments)
                elif name == "resume_browser_instance":
                    return await self._resume_browser_instance(arguments)
                elif name == "stop_browser_instance":
                    return await self._stop_browser_instance(arguments)
                elif name == "list_fingerprints":
                    return await self._list_fingerprints()
                elif name == "xhs_post_comment":
                    return await self._xhs_post_comment(arguments)
                elif name == "xhs_like_feed":
                    return await self._xhs_like_feed(arguments)
                elif name == "xhs_favorite_feed":
                    return await self._xhs_favorite_feed(arguments)
                elif name == "xhs_list_feeds":
                    return await self._xhs_list_feeds(arguments)
                else:
                    raise ValueError(f"未知工具: {name}")

            except Exception as e:
                self.logger.error(f"工具调用失败 {name}: {e}")
                return [
                    types.TextContent(
                        type="text",
                        text=f"工具调用失败: {str(e)}"
                    )
                ]

    async def _create_browser_instance(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """创建浏览器实例"""
        profile_name = arguments["profile_name"]
        fingerprint_name = arguments["fingerprint_name"]
        headless = arguments.get("headless", False)

        # 创建浏览器配置
        profile = self.fingerprint_manager.create_browser_profile(
            name=profile_name,
            fingerprint_name=fingerprint_name,
            headless=headless
        )

        # 创建浏览器实例
        instance = await self.browser_pool.create_instance(profile)

        return [
            types.TextContent(
                type="text",
                text=f"创建浏览器实例成功:\n"
                     f"- 实例ID: {instance.instance_id}\n"
                     f"- 配置名称: {profile.name}\n"
                     f"- 指纹配置: {fingerprint_name}\n"
                     f"- 无头模式: {headless}\n"
                     f"- 状态: {instance.status}"
            )
        ]

    async def _list_browser_instances(self) -> List[types.TextContent]:
        """列出所有浏览器实例"""
        instances = await self.browser_pool.get_all_instances()

        if not instances:
            return [
                types.TextContent(
                    type="text",
                    text="没有运行的浏览器实例"
                )
            ]

        instances_text = "浏览器实例列表:\n"
        for instance in instances:
            account_info = f" - 账户: {instance.account.username}" if instance.account else " - 未登录"
            instances_text += (
                f"- 实例ID: {instance.instance_id}\n"
                f"  配置: {instance.profile.name}\n"
                f"  状态: {instance.status}\n"
                f"{account_info}\n"
                f"  创建时间: {instance.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )

        return [
            types.TextContent(
                type="text",
                text=instances_text
            )
        ]

    async def _xhs_login(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """小红书扫码登录"""
        instance_id = arguments["instance_id"]

        account = await self.xhs_service.login(instance_id)

        return [
            types.TextContent(
                type="text",
                text=f"登录成功!\n"
                     f"- 用户名: {account.username}\n"
                     f"- 昵称: {account.nickname or '未知'}\n"
                     f"- 登录状态: {'已登录' if account.is_logged_in else '未登录'}\n"
                     f"- 最后登录: {account.last_login.strftime('%Y-%m-%d %H:%M:%S') if account.last_login else '未知'}"
            )
        ]

    async def _xhs_publish_note(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """发布小红书笔记"""
        instance_id = arguments["instance_id"]
        content = arguments["content"]
        images = arguments.get("images", [])
        tags = arguments.get("tags", [])

        result = await self.xhs_service.publish_note(instance_id, content, images, tags)

        return [
            types.TextContent(
                type="text",
                text=f"发布成功!\n"
                     f"- 内容: {content[:100]}...\n"
                     f"- 图片数量: {len(images)}\n"
                     f"- 标签数量: {len(tags)}\n"
                     f"- 消息: {result.get('message', '发布完成')}"
            )
        ]

    async def _xhs_search(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """小红书搜索"""
        instance_id = arguments["instance_id"]
        keyword = arguments["keyword"]
        limit = arguments.get("limit", 10)

        results = await self.xhs_service.search(instance_id, keyword, limit)

        if not results:
            return [
                types.TextContent(
                    type="text",
                    text=f"搜索 '{keyword}' 没有找到结果"
                )
            ]

        results_text = f"搜索 '{keyword}' 结果 ({len(results)} 个):\n\n"
        for result in results:
            results_text += (
                f"{result['index']}. {result['title']}\n"
                f"   内容: {result['content'][:100]}...\n"
                f"   作者: {result['author']}\n\n"
            )

        return [
            types.TextContent(
                type="text",
                text=results_text
            )
        ]

    async def _pause_browser_instance(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """暂停浏览器实例"""
        instance_id = arguments["instance_id"]

        success = await self.browser_pool.pause_instance(instance_id)

        if success:
            return [
                types.TextContent(
                    type="text",
                    text=f"已暂停浏览器实例: {instance_id}"
                )
            ]
        else:
            return [
                types.TextContent(
                    type="text",
                    text=f"暂停浏览器实例失败: {instance_id}"
                )
            ]

    async def _resume_browser_instance(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """恢复浏览器实例"""
        instance_id = arguments["instance_id"]

        success = await self.browser_pool.resume_instance(instance_id)

        if success:
            return [
                types.TextContent(
                    type="text",
                    text=f"已恢复浏览器实例: {instance_id}"
                )
            ]
        else:
            return [
                types.TextContent(
                    type="text",
                    text=f"恢复浏览器实例失败: {instance_id}"
                )
            ]

    async def _stop_browser_instance(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """停止浏览器实例"""
        instance_id = arguments["instance_id"]

        success = await self.browser_pool.stop_instance(instance_id)

        if success:
            return [
                types.TextContent(
                    type="text",
                    text=f"已停止浏览器实例: {instance_id}"
                )
            ]
        else:
            return [
                types.TextContent(
                    type="text",
                    text=f"停止浏览器实例失败: {instance_id}"
                )
            ]

    async def _list_fingerprints(self) -> List[types.TextContent]:
        """列出所有指纹配置"""
        fingerprints = self.fingerprint_manager.get_all_fingerprints()

        if not fingerprints:
            return [
                types.TextContent(
                    type="text",
                    text="没有可用的指纹配置"
                )
            ]

        fingerprints_text = "可用的指纹配置:\n"
        for name, fingerprint in fingerprints.items():
            fingerprints_text += (
                f"- {name}:\n"
                f"   User-Agent: {fingerprint.user_agent[:50]}...\n"
                f"   视口: {fingerprint.viewport['width']}x{fingerprint.viewport['height']}\n"
                f"   平台: {fingerprint.platform}\n"
                f"   语言: {fingerprint.language}\n"
                f"   时区: {fingerprint.timezone}\n\n"
            )

        return [
            types.TextContent(
                type="text",
                text=fingerprints_text
            )
        ]

    async def _xhs_post_comment(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """发表评论到指定笔记"""
        instance_id = arguments["instance_id"]
        feed_id = arguments["feed_id"]
        content = arguments["content"]

        result = await self.xhs_service.post_comment(instance_id, feed_id, content)

        return [
            types.TextContent(
                type="text",
                text=f"评论发表成功!\n"
                     f"- 笔记ID: {result.get('feed_id', '未知')}\n"
                     f"- 评论内容: {content[:50]}...\n"
                     f"- 消息: {result.get('message', '评论发表成功')}"
            )
        ]

    async def _xhs_like_feed(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """点赞/取消点赞指定笔记"""
        instance_id = arguments["instance_id"]
        feed_id = arguments["feed_id"]
        unlike = arguments.get("unlike", False)

        result = await self.xhs_service.like_feed(instance_id, feed_id, unlike)

        action = "取消点赞" if unlike else "点赞"
        return [
            types.TextContent(
                type="text",
                text=f"{action}成功!\n"
                     f"- 笔记ID: {result.get('feed_id', '未知')}\n"
                     f"- 消息: {result.get('message', f'{action}成功')}"
            )
        ]

    async def _xhs_favorite_feed(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """收藏/取消收藏指定笔记"""
        instance_id = arguments["instance_id"]
        feed_id = arguments["feed_id"]
        unfavorite = arguments.get("unfavorite", False)

        result = await self.xhs_service.favorite_feed(instance_id, feed_id, unfavorite)

        action = "取消收藏" if unfavorite else "收藏"
        return [
            types.TextContent(
                type="text",
                text=f"{action}成功!\n"
                     f"- 笔记ID: {result.get('feed_id', '未知')}\n"
                     f"- 消息: {result.get('message', f'{action}成功')}"
            )
        ]

    async def _xhs_list_feeds(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """获取 Feed 列表"""
        instance_id = arguments["instance_id"]
        limit = arguments.get("limit", 20)

        feeds = await self.xhs_service.list_feeds(instance_id, limit)

        if not feeds:
            return [
                types.TextContent(
                    type="text",
                    text="没有找到 Feed"
                )
            ]

        feeds_text = f"Feed 列表 ({len(feeds)} 个):\n\n"
        for feed in feeds:
            feeds_text += (
                f"{feed['index']}. {feed['title'] or '无标题'}\n"
                f"   内容: {feed['content'][:100]}...\n"
                f"   作者: {feed['author']}\n"
                f"   点赞: {feed['likes']} | 评论: {feed['comments']}\n"
                f"   已点赞: {'是' if feed['liked'] else '否'} | 已收藏: {'是' if feed['collected'] else '否'}\n"
                f"   笔记ID: {feed['feed_id']}\n\n"
            )

        return [
            types.TextContent(
                type="text",
                text=feeds_text
            )
        ]

    async def initialize(self):
        """初始化服务器"""
        await self.browser_pool.initialize()
        self.logger.info("小红书 MCP 服务器初始化完成")

    async def run(self):
        """运行服务器"""
        await self.initialize()

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="xhs-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    async def cleanup(self):
        """清理资源"""
        await self.browser_pool.cleanup()
        self.logger.info("小红书 MCP 服务器清理完成")


def main():
    """主函数"""
    server = XHSMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()