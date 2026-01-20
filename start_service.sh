#!/bin/bash
# 启动 API 服务的脚本

cd "$(dirname "$0")"

echo "=========================================="
echo "启动任务调度器 API 服务"
echo "=========================================="
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "错误: 未找到虚拟环境 .venv"
    echo "请先创建虚拟环境: python3 -m venv .venv"
    exit 1
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source .venv/bin/activate

# 检查端口是否被占用
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "警告: 端口 8000 已被占用"
    echo "正在停止占用端口的进程..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 2
fi

# 启动服务
echo "启动 API 服务..."
echo "服务地址: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo "Web UI: http://localhost:8000/"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

python service/start_api.py --host 0.0.0.0 --port 8000 --reload
