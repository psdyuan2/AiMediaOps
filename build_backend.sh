#!/bin/bash
# 使用 PyInstaller 打包后端服务为可执行文件

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"

echo "============================================================"
echo "开始打包后端服务..."
echo "后端目录: $BACKEND_DIR"
echo "构建目录: $BUILD_DIR"
echo "输出目录: $DIST_DIR"
echo "============================================================"

# 自动激活虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "$SCRIPT_DIR/venv" ]; then
        echo "🔧 激活虚拟环境: $SCRIPT_DIR/venv"
        source "$SCRIPT_DIR/venv/bin/activate"
    elif [ -d "$SCRIPT_DIR/.venv" ]; then
        echo "🔧 激活虚拟环境: $SCRIPT_DIR/.venv"
        source "$SCRIPT_DIR/.venv/bin/activate"
    fi
fi

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  警告: 未检测到虚拟环境，建议在虚拟环境中运行此脚本"
    echo "   如果使用系统 Python，请确保已安装所有依赖"
fi

# 检查 PyInstaller 是否已安装
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "📦 安装 PyInstaller..."
    python3 -m pip install pyinstaller
fi

# 进入后端目录
cd "$BACKEND_DIR"

# 清理之前的构建
echo "🧹 清理之前的构建..."
rm -rf "$BUILD_DIR/backend" "$DIST_DIR/backend" build dist

# 运行 PyInstaller（从 backend 目录运行）
echo "🔨 开始打包..."
cd "$BACKEND_DIR"
python3 -m PyInstaller \
    --clean \
    --noconfirm \
    pyinstaller.spec

# 检查输出文件
EXE_PATH="$BACKEND_DIR/dist/moke-backend"
if [ -f "$EXE_PATH" ]; then
    echo "✅ 打包成功！"
    echo "可执行文件位置: $EXE_PATH"
    
    # 显示文件大小
    FILE_SIZE=$(du -h "$EXE_PATH" | cut -f1)
    echo "文件大小: $FILE_SIZE"
    
    # 复制可执行文件到 backend 目录根目录（供 Electron 使用）
    cp "$EXE_PATH" "$BACKEND_DIR/moke-backend"
    chmod +x "$BACKEND_DIR/moke-backend"
    echo "✅ 可执行文件已复制到: $BACKEND_DIR/moke-backend"
    
    # 测试可执行文件
    echo ""
    echo "🧪 测试可执行文件..."
    if timeout 5 "$EXE_PATH" 2>&1 | head -10 | grep -q "Started server process"; then
        echo "✅ 可执行文件可以运行"
    else
        echo "⚠️  可执行文件可能有问题，请检查"
    fi
else
    echo "❌ 打包失败：未找到可执行文件"
    exit 1
fi

echo ""
echo "============================================================"
echo "打包完成！"
echo "可执行文件: $EXE_PATH"
echo "============================================================"
