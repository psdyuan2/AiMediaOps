#!/usr/bin/env python3
"""
后端服务入口点 - 用于 PyInstaller 打包
"""
import sys
import os
import uvicorn

# 添加后端目录到 Python 路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 导入 FastAPI 应用
from app.api.main import app

if __name__ == "__main__":
    # 从环境变量获取配置，如果没有则使用默认值
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8765"))
    log_level = os.getenv("API_LOG_LEVEL", "info")
    
    # 启动 uvicorn 服务器
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level
    )
