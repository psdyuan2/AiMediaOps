# Electron 应用打包方案

## 概述

本项目使用 Electron 将 Python 后端 + React 前端打包成桌面应用。

## 项目结构

```
.
├── electron/              # Electron 主进程代码
│   ├── main.js           # 主进程入口
│   └── preload.js        # 预加载脚本（安全通信桥接）
├── frontend/              # React 前端应用
├── backend/               # 后端文件（打包时复制）
│   ├── app/              # Python 应用代码
│   ├── service/          # 服务代码
│   ├── venv/             # Python 虚拟环境（打包时复制）
│   ├── requirements.txt  # Python 依赖
│   └── start_backend.sh  # 后端启动脚本
├── build/                 # 构建资源（图标、配置文件等）
├── package.json          # Electron 项目配置
└── build_electron_app.sh # 一键打包脚本
```

## 功能特性

### 1. 后端服务自动启动
- 应用启动时自动启动 Python 后端服务
- 优先使用打包的 venv（如果可用）
- 如果打包 venv 不可用，自动创建运行时 venv 并安装依赖

### 2. 启动卡片
- 应用启动时显示启动卡片
- 实时显示后端启动日志（bootstrap.log 和 backend.log）
- 等待后端服务就绪后才显示主界面

### 3. 日志监控
- 实时监控 `~/.moke/logs/bootstrap.log` 和 `backend.log`
- 通过 IPC 将日志推送到前端显示

## 开发模式

### 启动开发环境

```bash
# 安装依赖
npm install
cd frontend && npm install && cd ..

# 启动开发模式（前端 + Electron）
npm run dev
```

开发模式会：
1. 启动 Vite 开发服务器（前端）
2. 等待前端就绪后启动 Electron
3. Electron 会连接到 `http://localhost:5173`

### 单独启动

```bash
# 只启动前端
npm run dev:frontend

# 只启动 Electron（需要前端已运行）
npm run dev:electron
```

## 打包应用

### 一键打包

```bash
./build_electron_app.sh
```

打包脚本会：
1. 检查环境（Node.js、npm、Python）
2. 安装依赖
3. 准备后端环境（复制文件、venv、Chromium）
4. 构建前端
5. 使用 electron-builder 打包

### 手动打包

```bash
# 1. 构建前端
cd frontend && npm run build && cd ..

# 2. 准备后端（复制到 backend/ 目录）
# 3. 打包 Electron
npm run build:electron
```

## 打包配置

### electron-builder 配置

配置文件：`package.json` 中的 `build` 字段

主要配置：
- **files**: 指定要打包的文件
- **extraResources**: 将 backend 目录作为额外资源打包
- **mac**: macOS 打包配置（DMG）
- **win**: Windows 打包配置（NSIS）
- **linux**: Linux 打包配置（AppImage）

### 包含的内容

打包时会包含：
- Electron 主进程代码（`electron/`）
- 前端构建产物（`frontend/dist/`）
- 后端代码（`backend/app/`、`backend/service/`）
- Python 虚拟环境（`backend/venv/`，如果存在）
- Playwright Chromium（`backend/playwright-browsers/`，如果存在）

### 排除的内容

打包时会排除：
- `__pycache__` 目录
- `*.pyc` 文件
- venv 中的激活脚本、pip 等工具

## 后端启动流程

1. **检查打包的 venv**
   - 如果存在且可用，直接使用
   - 设置 `PLAYWRIGHT_BROWSERS_PATH` 指向打包的 Chromium

2. **检查运行时 venv**
   - 如果 `~/.moke/venv` 存在，使用它并更新依赖
   - 如果不存在，创建新的 venv 并安装依赖

3. **启动 uvicorn**
   - 监听 `127.0.0.1:8765`
   - 日志输出到 `~/.moke/logs/backend.log`

## 日志文件

应用运行时会在 `~/.moke/logs/` 目录下创建：

- `bootstrap.log`: 后端启动脚本的日志
- `backend.log`: uvicorn 服务的日志

## 故障排查

### 后端启动失败

1. 检查日志：`~/.moke/logs/bootstrap.log` 和 `backend.log`
2. 检查 Python 版本：需要 >= 3.10
3. 检查依赖：如果使用运行时 venv，确保依赖已安装

### 前端无法连接后端

1. 检查后端是否运行：`lsof -iTCP:8765 -sTCP:LISTEN`
2. 检查启动卡片中的日志
3. 检查后端日志文件

### 打包失败

1. 确保所有依赖已安装
2. 确保前端已构建（`frontend/dist/` 存在）
3. 确保后端文件已复制到 `backend/` 目录
4. 检查 electron-builder 配置

## 注意事项

1. **venv 大小**: 打包的 venv 会增加应用体积（约 300MB+）
2. **Python 版本**: 打包的 venv 需要与目标系统的 Python 版本兼容
3. **Chromium**: Playwright Chromium 也会增加应用体积（约 100MB+）
4. **首次启动**: 如果使用运行时 venv，首次启动需要安装依赖，可能需要几分钟

## 下一步优化

- [ ] 使用 PyInstaller 打包 Python 为独立可执行文件
- [ ] 压缩 venv，减少应用体积
- [ ] 添加自动更新功能
- [ ] 优化启动速度
