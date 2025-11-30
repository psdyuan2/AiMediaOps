#!/usr/bin/env python3
"""
小红书 MCP 服务器启动脚本

启动 MCP 服务器，提供小红书操作工具。
"""

import asyncio
import logging

from app.xhs_mcp.mcp_server.server import XHSMCPServer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    server = XHSMCPServer()

    try:
        logger.info("启动小红书 MCP 服务器...")
        await server.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器运行错误: {e}")
    finally:
        await server.cleanup()
        logger.info("服务器已关闭")


if __name__ == "__main__":
    asyncio.run(main())