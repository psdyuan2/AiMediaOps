#!/bin/bash
# 启动 PyInstaller 打包的后端可执行文件

set -e

# 获取脚本所在目录（应用资源目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}"

# 从环境变量获取资源目录（由 Electron 设置）
APP_RESOURCES="${APP_RESOURCES:-$BACKEND_DIR}"
# 运行时数据目录（日志、数据库等）
APP_DATA_DIR="${APP_DATA_DIR:-$HOME/.moke}"
export APP_DATA_DIR

# 创建应用数据目录（用于日志、数据库等）
mkdir -p "$APP_DATA_DIR/logs"
BOOTSTRAP_LOG="$APP_DATA_DIR/logs/bootstrap.log"
# 记录脚本自身的输出，便于排障
exec >> "$BOOTSTRAP_LOG" 2>&1
echo "============================================================"
echo "$(date '+%Y-%m-%d %H:%M:%S') MoKe backend bootstrap (Binary)"
echo "APP_RESOURCES=$APP_RESOURCES"
echo "APP_DATA_DIR=$APP_DATA_DIR"

# 函数：检查并关闭占用指定端口的进程
kill_port_process() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        # macOS/Linux 使用 lsof
        local pid=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$pid" ]; then
            echo "⚠️  发现端口 $port 被进程 $pid 占用，正在关闭..."
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
            # 再次检查是否已关闭
            if lsof -ti:$port >/dev/null 2>&1; then
                echo "❌ 无法关闭占用端口 $port 的进程"
                return 1
            else
                echo "✅ 已成功关闭占用端口 $port 的进程"
                return 0
            fi
        fi
    elif command -v netstat >/dev/null 2>&1; then
        # 备用方案：使用 netstat（macOS）
        local pid=$(netstat -anv | grep ":$port " | grep LISTEN | awk '{print $9}' | head -1)
        if [ -n "$pid" ] && [ "$pid" != "-" ]; then
            echo "⚠️  发现端口 $port 被进程 $pid 占用，正在关闭..."
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
            echo "✅ 已尝试关闭占用端口 $port 的进程"
            return 0
        fi
    fi
    return 0
}

# 设置 Playwright 浏览器路径
# 优先使用 Electron 传递的环境变量
if [ -n "$PLAYWRIGHT_BROWSERS_PATH" ]; then
    export PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_BROWSERS_PATH"
    echo "✅ 使用 Electron 传递的 Chromium 路径: $PLAYWRIGHT_BROWSERS_PATH"
elif [ -n "$APP_RESOURCES" ] && [ -d "$APP_RESOURCES/backend/playwright-browsers" ]; then
    export PLAYWRIGHT_BROWSERS_PATH="$APP_RESOURCES/backend/playwright-browsers"
    echo "✅ 使用打包的 Chromium (backend): $PLAYWRIGHT_BROWSERS_PATH"
elif [ -n "$APP_RESOURCES" ] && [ -d "$APP_RESOURCES/playwright-browsers" ]; then
    export PLAYWRIGHT_BROWSERS_PATH="$APP_RESOURCES/playwright-browsers"
    echo "✅ 使用打包的 Chromium (root): $PLAYWRIGHT_BROWSERS_PATH"
else
    # 开发环境回退到默认路径
    export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
    echo "⚠️  使用默认 Chromium 路径: $PLAYWRIGHT_BROWSERS_PATH"
fi

# 查找可执行文件
BINARY_PATH="$BACKEND_DIR/moke-backend"
if [ ! -f "$BINARY_PATH" ]; then
    # 尝试在 dist 目录中查找
    BINARY_PATH="$BACKEND_DIR/dist/moke-backend"
fi

if [ ! -f "$BINARY_PATH" ]; then
    echo "❌ 错误: 未找到后端可执行文件"
    echo "   查找路径: $BACKEND_DIR/moke-backend"
    echo "   查找路径: $BACKEND_DIR/dist/moke-backend"
    exit 1
fi

# 确保可执行文件有执行权限
chmod +x "$BINARY_PATH"

# 设置工作目录为后端目录
cd "$BACKEND_DIR"

# 设置环境变量
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
export API_HOST="127.0.0.1"
export API_PORT="8765"
export API_LOG_LEVEL="info"

# 检查并关闭占用 8765 端口的进程
kill_port_process 8765

# 启动后端服务
echo "🚀 启动 MoKe 后端服务（二进制版本）..."
echo "   工作目录: $BACKEND_DIR"
echo "   可执行文件: $BINARY_PATH"
echo "   端口: $API_PORT"
echo "   日志目录: $APP_DATA_DIR/logs"

# 将输出重定向到日志文件
LOG_FILE="$APP_DATA_DIR/logs/backend.log"
exec "$BINARY_PATH" >> "$LOG_FILE" 2>&1
