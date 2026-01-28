"""
配置文件 - 存储应用程序配置常量

本文件包含应用程序的配置常量，如：
1. 日志级别和格式配置
2. MCP服务URL配置
3. 其他系统配置

配置可以通过环境变量覆盖。
"""

import os

# ==================== 日志配置 ====================
# 日志级别配置
LOG_LEVEL = os.getenv("XHS_LOG_LEVEL", "DEBUG").upper()
LOG_ENABLE_COLOR = os.getenv("XHS_LOG_COLOR", "true").lower() in ["true", "1", "yes"]
LOG_SHOW_TIMESTAMP = os.getenv("XHS_LOG_TIMESTAMP", "true").lower() in ["true", "1", "yes"]
LOG_SHOW_MODULE = os.getenv("XHS_LOG_MODULE", "true").lower() in ["true", "1", "yes"]
LOG_SHOW_FUNCTION = os.getenv("XHS_LOG_FUNCTION", "false").lower() in ["true", "1", "yes"]
LOG_TO_FILE = os.getenv("XHS_LOG_TO_FILE", "false").lower() in ["true", "1", "yes"]
LOG_FILE_PATH = os.getenv("XHS_LOG_FILE_PATH", "logs/xiaohongshu_agent.log")

# ==================== MCP服务配置 ====================
# MCP服务URL配置
XHS_MCP_SERVICE_URL = "http://localhost:18060/mcp"

# ==================== 系统配置 ====================
# 系统类型配置
SYS_TYPE_WIN_64 = "win64"
SYS_TYPE_MAC_INTEL = "mac_intel"
SYS_TYPE_MAC_SILICON = "mac_silicon"

__all__ = [
    # 日志配置
    "LOG_LEVEL",
    "LOG_ENABLE_COLOR",
    "LOG_SHOW_TIMESTAMP",
    "LOG_SHOW_MODULE",
    "LOG_SHOW_FUNCTION",
    "LOG_TO_FILE",
    "LOG_FILE_PATH",

    # MCP服务配置
    "XHS_MCP_SERVICE_URL",

    # 系统配置
    "SYS_TYPE_WIN_64",
    "SYS_TYPE_MAC_INTEL",
    "SYS_TYPE_MAC_SILICON",
]