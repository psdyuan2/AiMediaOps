"""
小红书智能体模块 - 基于MCP协议的小红书操作自动化

本模块提供基于Model Context Protocol (MCP)的小红书操作智能体，支持：
- 小红书内容发布（图文、视频）
- 内容搜索和浏览
- 互动操作（点赞、评论、收藏）
- 用户管理和登录状态检查

通过MCP协议与小红书操作服务通信，实现稳定可靠的小红书自动化运营。
"""

from .agent import XiaohongshuAgent

__all__ = [
    "XiaohongshuAgent",
]

__version__ = "1.0.0"
__author__ = "Senior Python Backend Architect"