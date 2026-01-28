#!/bin/bash
# 为 Electron 桌面应用启动后端服务的脚本

set -e

# 获取脚本所在目录（应用资源目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}"

# 从环境变量获取资源目录（由 Electron 设置）
APP_RESOURCES="${APP_RESOURCES:-$BACKEND_DIR}"
# 运行时数据目录（日志、运行时 venv 等）
APP_DATA_DIR="${APP_DATA_DIR:-$HOME/.moke}"
export APP_DATA_DIR

# 创建应用数据目录（用于日志、数据库等）
mkdir -p "$APP_DATA_DIR/logs"
BOOTSTRAP_LOG="$APP_DATA_DIR/logs/bootstrap.log"
# 记录脚本自身的输出，便于排障（uvicorn 输出仍单独进 backend.log）
exec >> "$BOOTSTRAP_LOG" 2>&1
echo "============================================================"
echo "$(date '+%Y-%m-%d %H:%M:%S') MoKe backend bootstrap"
echo "APP_RESOURCES=$APP_RESOURCES"
echo "APP_DATA_DIR=$APP_DATA_DIR"

# 设置 Playwright 浏览器路径
if [ -n "$APP_RESOURCES" ] && [ -d "$APP_RESOURCES/playwright-browsers" ]; then
    export PLAYWRIGHT_BROWSERS_PATH="$APP_RESOURCES/playwright-browsers"
    echo "✅ 使用打包的 Chromium: $PLAYWRIGHT_BROWSERS_PATH"
else
    # 开发环境回退到默认路径
    export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
    echo "⚠️  使用默认 Chromium 路径: $PLAYWRIGHT_BROWSERS_PATH"
fi

# Python 虚拟环境优先级：
# 1. 优先使用打包的 venv（如果存在且可用）
# 2. 其次使用运行时 venv（~/.moke/venv，如果存在）
# 3. 最后创建新的运行时 venv

BUNDLED_VENV="$BACKEND_DIR/venv"
RUNTIME_VENV="$APP_DATA_DIR/venv"
PYTHON_BIN=""

# 优先尝试使用打包的 venv（如果存在且可用，直接使用，跳过系统 Python 检查）
if [ -d "$BUNDLED_VENV" ] && [ -f "$BUNDLED_VENV/bin/python3" ]; then
    # 测试打包的 venv 是否可用
    if "$BUNDLED_VENV/bin/python3" -c "import sys; sys.exit(0)" 2>/dev/null; then
        # 验证关键依赖是否可用
        if "$BUNDLED_VENV/bin/python3" -c "import anyio._backends" 2>/dev/null; then
            PYTHON_BIN="$BUNDLED_VENV/bin/python3"
            PYTHON_VERSION=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            echo "✅ 使用打包的虚拟环境: $BUNDLED_VENV (Python $PYTHON_VERSION)"
            
            # 确保 venv 的 site-packages 在 Python 路径中
            unset PYTHONHOME
            export VIRTUAL_ENV="$BUNDLED_VENV"
        else
            echo "⚠️  打包的 venv 依赖不完整，将使用运行时 venv"
        fi
    else
        echo "⚠️  打包的 venv 不可用，将使用运行时 venv"
    fi
fi

# 如果打包的 venv 不可用，需要检查系统 Python（用于创建运行时 venv）
if [ -z "$PYTHON_BIN" ]; then
    # 检查系统是否有 python3
    if ! command -v python3 >/dev/null 2>&1; then
        echo "❌ 错误: 未找到 python3，请在系统中安装 Python 3 后重试。"
        exit 1
    fi

    # 检查系统 Python 版本（需要 >= 3.10）
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        echo "❌ 错误: Python 版本需要 >= 3.10，当前版本: $PYTHON_VERSION"
        exit 1
    fi
fi

# 如果打包的 venv 不可用，尝试使用或创建运行时 venv
if [ -z "$PYTHON_BIN" ]; then
    if [ -d "$RUNTIME_VENV" ] && [ -f "$RUNTIME_VENV/bin/python3" ]; then
        PYTHON_BIN="$RUNTIME_VENV/bin/python3"
        echo "✅ 使用现有运行时虚拟环境: $RUNTIME_VENV"
        # 检查并更新依赖（确保所有依赖都已安装，特别是新添加的依赖）
        echo "📦 检查并更新依赖（确保所有依赖都已安装）..."
        "$PYTHON_BIN" -m pip install -q --upgrade pip
        "$PYTHON_BIN" -m pip install -q -r "$BACKEND_DIR/requirements.txt"
        echo "✅ 依赖检查完成"
    else
        echo "📦 未检测到运行时虚拟环境，正在创建: $RUNTIME_VENV"
        python3 -m venv "$RUNTIME_VENV"
        PYTHON_BIN="$RUNTIME_VENV/bin/python3"
        echo "📦 安装后端依赖（首次运行可能需要较长时间）..."
        "$PYTHON_BIN" -m pip install -q --upgrade pip
        "$PYTHON_BIN" -m pip install -q -r "$BACKEND_DIR/requirements.txt"
        echo "✅ 依赖安装完成"
    fi
fi

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

# 设置工作目录为后端目录
cd "$BACKEND_DIR"

# 设置环境变量
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
export API_HOST="127.0.0.1"
export API_PORT="8765"
export API_LOG_LEVEL="info"

# 检查并关闭占用 8765 端口的进程
kill_port_process 8765

# 如果使用打包的 venv，确保 Python 使用 venv 的路径而不是系统路径
if [ "$PYTHON_BIN" = "$BUNDLED_VENV/bin/python3" ]; then
    # 清除可能干扰的 Python 环境变量
    unset PYTHONHOME
    export VIRTUAL_ENV="$BUNDLED_VENV"
    # 确保 Python 解释器使用 venv 的 site-packages
    export PYTHONPATH="$BUNDLED_VENV/lib/python3.11/site-packages:$PYTHONPATH"
fi

# 确保使用 venv 的 Python 解释器，而不是系统 Python
# 如果使用打包的 venv，需要确保 Python 解释器路径正确
if [ -n "$PYTHON_BIN" ] && [ -f "$PYTHON_BIN" ]; then
    # 验证 Python 解释器是否可用
    if ! "$PYTHON_BIN" -c "import sys; sys.exit(0)" 2>/dev/null; then
        echo "❌ 错误: Python 解释器不可用: $PYTHON_BIN"
        exit 1
    fi
    
    # 验证关键依赖是否可用（仅在运行时 venv 中修复，打包的 venv 应该已经完整）
    if [ "$PYTHON_BIN" != "$BUNDLED_VENV/bin/python3" ]; then
        if ! "$PYTHON_BIN" -c "import anyio._backends" 2>/dev/null; then
            echo "⚠️  警告: anyio._backends 模块不可用，尝试重新安装 anyio..."
            "$PYTHON_BIN" -m pip install --force-reinstall --no-cache-dir anyio >/dev/null 2>&1
        fi
    fi
fi

# 启动后端服务
echo "🚀 启动 MoKe 后端服务..."
echo "   工作目录: $BACKEND_DIR"
echo "   Python: $PYTHON_BIN"
echo "   端口: $API_PORT"
echo "   日志目录: $APP_DATA_DIR/logs"

# 将输出重定向到日志文件
LOG_FILE="$APP_DATA_DIR/logs/backend.log"
exec "$PYTHON_BIN" -m uvicorn app.api.main:app \
    --host "$API_HOST" \
    --port "$API_PORT" \
    --log-level "$API_LOG_LEVEL" \
    >> "$LOG_FILE" 2>&1
