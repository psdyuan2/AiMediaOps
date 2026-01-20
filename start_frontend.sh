#!/bin/bash
# 启动前端服务的脚本

cd "$(dirname "$0")"

echo "=========================================="
echo "启动前端开发服务"
echo "=========================================="
echo ""

# 检查前端目录是否存在
if [ ! -d "frontend" ]; then
    echo "错误: 未找到前端目录 frontend"
    exit 1
fi

# 进入前端目录
cd frontend

# 检查 node_modules 是否存在
if [ ! -d "node_modules" ]; then
    echo "警告: 未找到 node_modules 目录"
    echo "正在安装依赖..."
    if command -v npm &> /dev/null; then
        npm install
        if [ $? -ne 0 ]; then
            echo "错误: 依赖安装失败"
            exit 1
        fi
    else
        echo "错误: 未找到 npm 命令，请先安装 Node.js"
        exit 1
    fi
fi

# 检查 Node.js 是否安装
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 Node.js，请先安装 Node.js"
    exit 1
fi

# 检查 npm 是否安装
if ! command -v npm &> /dev/null; then
    echo "错误: 未找到 npm，请先安装 Node.js"
    exit 1
fi

# 检查端口是否被占用
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "警告: 端口 3000 已被占用"
    echo "正在停止占用端口的进程..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null
    sleep 2
fi

# 启动服务
echo "启动前端开发服务器..."
echo "服务地址: http://localhost:3000"
echo "API 代理: http://localhost:3000/api -> http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

npm run dev
