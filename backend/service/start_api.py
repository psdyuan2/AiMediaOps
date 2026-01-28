#!/usr/bin/env python3
"""
任务调度器 API 服务启动脚本

用法:
    python service/start_api.py
    python service/start_api.py --host 0.0.0.0 --port 8000
    python service/start_api.py --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import argparse
import uvicorn
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="启动任务调度器 API 服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 使用默认配置启动
  %(prog)s --port 8080               # 指定端口
  %(prog)s --host 127.0.0.1         # 指定主机
  %(prog)s --reload                 # 开发模式（自动重载）
  %(prog)s --workers 4              # 生产模式（多进程）
        """
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("API_HOST", "0.0.0.0"),
        help="绑定主机地址 (默认: 0.0.0.0, 可通过环境变量 API_HOST 设置)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("API_PORT", "8000")),
        help="绑定端口 (默认: 8000, 可通过环境变量 API_PORT 设置)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("API_RELOAD", "false").lower() in ["true", "1", "yes"],
        help="开发模式：代码变更时自动重载 (可通过环境变量 API_RELOAD 设置)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("API_WORKERS", "1")),
        help="工作进程数，生产环境建议设置为 CPU 核心数 (默认: 1, 可通过环境变量 API_WORKERS 设置)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.getenv("API_LOG_LEVEL", "info"),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="日志级别 (默认: info, 可通过环境变量 API_LOG_LEVEL 设置)"
    )
    
    parser.add_argument(
        "--access-log",
        action="store_true",
        default=os.getenv("API_ACCESS_LOG", "false").lower() in ["true", "1", "yes"],
        help="启用访问日志 (可通过环境变量 API_ACCESS_LOG 设置)"
    )
    
    parser.add_argument(
        "--app-dir",
        type=str,
        default="app.api.main:app",
        help="应用模块路径 (默认: app.api.main:app)"
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 打印启动信息
    print("=" * 60)
    print("任务调度器 API 服务")
    print("=" * 60)
    print(f"主机: {args.host}")
    print(f"端口: {args.port}")
    print(f"重载模式: {'是' if args.reload else '否'}")
    print(f"工作进程数: {args.workers}")
    print(f"日志级别: {args.log_level}")
    print(f"访问日志: {'启用' if args.access_log else '禁用'}")
    print("=" * 60)
    print(f"\nAPI 文档地址:")
    print(f"  - Swagger UI: http://{args.host}:{args.port}/docs")
    print(f"  - ReDoc: http://{args.host}:{args.port}/redoc")
    print(f"\n按 Ctrl+C 停止服务\n")
    
    # 配置 uvicorn
    config = {
        "app": args.app_dir,
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "access_log": args.access_log,
        "timeout_keep_alive": int(os.getenv("API_TIMEOUT_KEEP_ALIVE", "600")),  # Keep-alive 超时（秒），默认10分钟
        "timeout_graceful_shutdown": int(os.getenv("API_TIMEOUT_GRACEFUL_SHUTDOWN", "30")),  # 优雅关闭超时（秒）
    }
    
    # 开发模式：单进程 + 自动重载
    if args.reload:
        config["reload"] = True
        config["reload_dirs"] = [str(project_root / "app")]
        uvicorn.run(**config)
    
    # 生产模式：多进程
    elif args.workers > 1:
        config["workers"] = args.workers
        uvicorn.run(**config)
    
    # 单进程模式
    else:
        uvicorn.run(**config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n服务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n启动失败: {e}", file=sys.stderr)
        sys.exit(1)

