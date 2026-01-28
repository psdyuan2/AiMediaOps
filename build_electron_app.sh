#!/bin/bash
# Electron 应用一键打包脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  MoKe Electron 应用打包脚本${NC}"
echo -e "${GREEN}========================================${NC}\n"

# 步骤 1: 检查环境
echo -e "${YELLOW}[步骤 1] 检查环境${NC}"
echo "----------------------------------------"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 未找到 Node.js，请先安装 Node.js${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node.js: $(node --version)${NC}"

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ 未找到 npm${NC}"
    exit 1
fi
echo -e "${GREEN}✅ npm: $(npm --version)${NC}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到 Python 3${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✅ Python: $PYTHON_VERSION${NC}"

# 步骤 2: 安装依赖
echo -e "\n${YELLOW}[步骤 2] 安装依赖${NC}"
echo "----------------------------------------"

# 安装根目录依赖（Electron）
if [ ! -d "node_modules" ]; then
    echo "安装 Electron 依赖..."
    npm install
else
    echo "检查 Electron 依赖..."
    npm install
fi

# 安装前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "安装前端依赖..."
    cd frontend
    npm install
    cd ..
else
    echo "检查前端依赖..."
    cd frontend
    npm install
    cd ..
fi

# 步骤 3: 准备后端环境
echo -e "\n${YELLOW}[步骤 3] 准备后端环境${NC}"
echo "----------------------------------------"

# 后端目录
BACKEND_DIR="$PROJECT_ROOT/backend"

# 确保启动脚本有执行权限
if [ -f "$BACKEND_DIR/start_backend.sh" ]; then
    chmod +x "$BACKEND_DIR/start_backend.sh"
fi
if [ -f "$BACKEND_DIR/start_backend_binary.sh" ]; then
    chmod +x "$BACKEND_DIR/start_backend_binary.sh"
fi

# 步骤 3.1: 同步帮助文档
echo -e "\n${YELLOW}[步骤 3.1] 同步帮助文档${NC}"
echo "----------------------------------------"

# 将 frontend/public/help_guide.md 同步到 docs/help_guide.md，确保打包时使用最新版本
if [ -f "$PROJECT_ROOT/frontend/public/help_guide.md" ]; then
    echo "同步帮助文档到 docs 目录..."
    cp "$PROJECT_ROOT/frontend/public/help_guide.md" "$PROJECT_ROOT/docs/help_guide.md"
    echo -e "${GREEN}✅ 帮助文档已同步${NC}"
else
    echo -e "${YELLOW}⚠️  未找到 frontend/public/help_guide.md${NC}"
fi

# 步骤 3.2: 使用 PyInstaller 打包后端
echo -e "\n${YELLOW}[步骤 3.2] 使用 PyInstaller 打包后端${NC}"
echo "----------------------------------------"

# 直接调用 build_backend.sh，确保逻辑统一且环境正确
if [ -f "$BACKEND_DIR/../build_backend.sh" ]; then
    echo "调用 build_backend.sh 进行打包..."
    "$BACKEND_DIR/../build_backend.sh"
    
    # 检查打包结果
    if [ ! -f "$BACKEND_DIR/moke-backend" ]; then
        echo -e "${RED}❌ 后端打包失败：未找到可执行文件${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ 未找到 build_backend.sh 脚本${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

# 步骤 3.3: 准备 Playwright 浏览器
echo -e "\n${YELLOW}[步骤 3.3] 准备 Playwright 浏览器${NC}"
echo "----------------------------------------"

# 尝试在虚拟环境中安装/更新浏览器
if [ -d "$BACKEND_DIR/venv" ]; then
    source "$BACKEND_DIR/venv/bin/activate"
    echo "在虚拟环境中运行 playwright install chromium..."
    # 安装 chromium 和 headless shell（使用 --only-shell 确保安装 headless shell）
    playwright install chromium --only-shell || playwright install chromium chromium-headless-shell || playwright install chromium
    deactivate
elif [ -d "$BACKEND_DIR/.venv" ]; then
    source "$BACKEND_DIR/.venv/bin/activate"
    echo "在虚拟环境中运行 playwright install chromium..."
    # 安装 chromium 和 headless shell
    playwright install chromium --only-shell || playwright install chromium chromium-headless-shell || playwright install chromium
    deactivate
else
    echo "尝试使用全局 playwright 安装..."
    playwright install chromium --only-shell || playwright install chromium chromium-headless-shell || playwright install chromium || echo "全局 playwright install 失败，尝试 python 模块..."
    python3 -m playwright install chromium --only-shell || python3 -m playwright install chromium chromium-headless-shell || python3 -m playwright install chromium || echo "无法安装 Playwright 浏览器"
fi

# 查找并复制 Chromium
# 注意：Playwright 可能使用 chromium-xxx 或 chromium_headless_shell-xxx
# macOS 上浏览器通常安装在 ~/Library/Caches/ms-playwright/ 而不是 ~/.cache/ms-playwright/
echo "搜索 Playwright 浏览器..."
# 尝试多个可能的缓存位置
PLAYWRIGHT_CACHE_PATHS=(
    "$HOME/Library/Caches/ms-playwright"
    "$HOME/.cache/ms-playwright"
    "$HOME/.local/share/ms-playwright"
)

PLAYWRIGHT_CACHE=""
for CACHE_PATH in "${PLAYWRIGHT_CACHE_PATHS[@]}"; do
    if [ -d "$CACHE_PATH" ]; then
        PLAYWRIGHT_CACHE="$CACHE_PATH"
        echo "找到 Playwright 缓存目录: $PLAYWRIGHT_CACHE"
        break
    fi
done

if [ -z "$PLAYWRIGHT_CACHE" ]; then
    echo -e "${RED}❌ 未找到 Playwright 缓存目录！${NC}"
    echo "请先运行: playwright install chromium"
    exit 1
fi

mkdir -p "$BACKEND_DIR/playwright-browsers"

# 查找所有 chromium 相关目录（包括 headless shell）
CHROMIUM_DIRS=$(find "$PLAYWRIGHT_CACHE" -maxdepth 1 \( -name "chromium-*" -o -name "chromium_headless_shell-*" \) 2>/dev/null | sort -r)

if [ -n "$CHROMIUM_DIRS" ]; then
    echo "找到以下 Chromium 浏览器："
    echo "$CHROMIUM_DIRS"
    
    # 复制所有找到的浏览器目录
    for CHROMIUM_DIR in $CHROMIUM_DIRS; do
        if [ -d "$CHROMIUM_DIR" ]; then
            DIR_NAME=$(basename "$CHROMIUM_DIR")
            DEST_DIR="$BACKEND_DIR/playwright-browsers/$DIR_NAME"
            
            # 移除旧的（如果存在）
            rm -rf "$DEST_DIR"
            
            echo "复制 $DIR_NAME 到: $DEST_DIR"
            cp -R "$CHROMIUM_DIR" "$BACKEND_DIR/playwright-browsers/"
            
            # 设置权限
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # 递归赋予执行权限
                chmod -R +x "$DEST_DIR"
            fi
        fi
    done
    
    echo -e "${GREEN}✅ 已复制所有 Chromium 浏览器并设置权限${NC}"
else
    echo -e "${RED}❌ 未找到 Playwright Chromium 浏览器！应用可能无法正常执行爬虫任务。${NC}"
    echo "请手动运行: cd backend && source venv/bin/activate && playwright install chromium --only-shell"
fi

echo -e "${GREEN}✅ 后端环境准备完成${NC}\n"

# 步骤 4: 构建前端
echo -e "${YELLOW}[步骤 4] 构建前端${NC}"
echo "----------------------------------------"
cd "$PROJECT_ROOT/frontend"
npm run build
cd "$PROJECT_ROOT"
echo -e "${GREEN}✅ 前端构建完成${NC}\n"

# 步骤 5: 打包 Electron 应用
echo -e "${YELLOW}[步骤 5] 打包 Electron 应用${NC}"
echo "----------------------------------------"
echo "清理之前的构建产物..."

# 彻底清理 DMG 挂载点（处理可能的残留）
echo "清理 DMG 挂载点..."
# 强制卸载所有可能的 MoKe 挂载
hdiutil detach "/Volumes/MoKe 1.0.0" -force 2>/dev/null || true
hdiutil detach "/Volumes/MoKe-1.0.0" -force 2>/dev/null || true
hdiutil detach "/Volumes/MoKe" -force 2>/dev/null || true

# 查找所有 MoKe 相关的挂载
MOUNTED_VOLUMES=$(hdiutil info 2>/dev/null | grep -E "image-path.*[Mm]o[Kk]e" | awk '{print $3}' | sort -u)
for VOL in $MOUNTED_VOLUMES; do
    if [ -n "$VOL" ]; then
        echo "尝试卸载: $VOL"
        hdiutil detach "$VOL" -force 2>/dev/null || true
    fi
done

# 清理 /Volumes 下的 MoKe 目录（如果存在）
if [ -d "/Volumes/MoKe 1.0.0" ]; then
    echo "强制清理残留挂载点: /Volumes/MoKe 1.0.0"
    rm -rf "/Volumes/MoKe 1.0.0" 2>/dev/null || true
fi
if [ -d "/Volumes/MoKe-1.0.0" ]; then
    echo "强制清理残留挂载点: /Volumes/MoKe-1.0.0"
    rm -rf "/Volumes/MoKe-1.0.0" 2>/dev/null || true
fi

# 等待一下确保清理完成
sleep 1

# 清理构建目录
rm -rf release

echo "开始 Electron 打包（这可能需要较长时间）..."
npm run build:electron

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  打包完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}安装包位置: release/${NC}"
