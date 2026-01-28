# Windows 平台 Electron 应用打包脚本构建逻辑文档

## 概述

本文档详细说明了 Windows 平台下 MoKe Electron 应用的完整打包流程和构建逻辑。本文档旨在帮助 Windows 平台上的开发者或 AI Coder 理解、测试和修正 Windows 版本的打包脚本。

## 目录结构

```
AiMediaOps/
├── build_electron_app.bat          # Windows 主构建脚本
├── build_backend.bat                # Windows 后端打包脚本
├── build_electron_app.sh            # macOS 主构建脚本（参考）
├── build_backend.sh                 # macOS 后端打包脚本（参考）
├── backend/
│   ├── start_backend_binary.bat     # Windows 后端启动脚本
│   ├── start_backend_binary.sh      # macOS 后端启动脚本（参考）
│   ├── moke-backend.exe             # Windows 后端可执行文件（构建后生成）
│   └── playwright-browsers/         # Playwright 浏览器目录（构建时复制）
├── frontend/
│   └── dist/                        # 前端构建输出目录
├── build/
│   ├── icon.icns                    # macOS 图标
│   └── icon.ico                     # Windows 图标（需要创建）
├── docs/
│   └── help_guide.md                # 帮助文档（构建时同步）
└── release/                         # 最终打包输出目录
```

## 构建流程详解

### 阶段 1: 环境检查

**脚本**: `build_electron_app.bat` (步骤 1)

**检查项**:
1. **Node.js**: 使用 `where node` 命令检查，必须安装 Node.js
2. **npm**: 使用 `where npm` 命令检查，通常随 Node.js 一起安装
3. **Python**: 使用 `where python` 命令检查，必须安装 Python 3.x

**关键点**:
- 如果任何一项检查失败，脚本会退出并显示错误信息
- Python 命令在 Windows 上可能是 `python` 而不是 `python3`

**常见问题**:
- Python 未添加到 PATH: 需要将 Python 安装目录添加到系统环境变量 PATH 中
- Node.js 版本过低: 建议使用 Node.js 16+ 版本

---

### 阶段 2: 依赖安装

**脚本**: `build_electron_app.bat` (步骤 2)

**操作**:
1. 检查 `node_modules` 目录是否存在
   - 不存在: 执行 `npm install` 安装根目录依赖（Electron 相关）
   - 存在: 执行 `npm install` 更新依赖
2. 检查 `frontend/node_modules` 目录是否存在
   - 不存在: 进入 `frontend` 目录执行 `npm install`
   - 存在: 进入 `frontend` 目录执行 `npm install` 更新

**关键点**:
- 使用 `call npm install` 而不是直接 `npm install`，确保在批处理脚本中正确执行
- 前端依赖安装完成后需要返回项目根目录

**常见问题**:
- 网络问题导致安装失败: 可能需要配置 npm 镜像源
- 权限问题: 可能需要以管理员身份运行

---

### 阶段 3: 后端环境准备

#### 3.1 同步帮助文档

**脚本**: `build_electron_app.bat` (步骤 3.1)

**操作**:
- 检查 `frontend/public/help_guide.md` 是否存在
- 如果存在，复制到 `docs/help_guide.md`
- 确保打包时使用最新版本的帮助文档

**关键点**:
- 使用 `copy /Y` 命令，`/Y` 参数表示覆盖已存在的文件时不提示
- 输出重定向到 `nul` 以隐藏复制成功的消息

---

#### 3.2 使用 PyInstaller 打包后端

**脚本**: `build_electron_app.bat` (步骤 3.2) → 调用 `build_backend.bat`

**详细流程** (`build_backend.bat`):

1. **虚拟环境激活**:
   - 检查 `venv\Scripts\activate.bat` 是否存在
   - 检查 `.venv\Scripts\activate.bat` 是否存在
   - 如果找到，使用 `call` 命令激活虚拟环境
   - Windows 虚拟环境激活命令: `call venv\Scripts\activate.bat`

2. **PyInstaller 检查**:
   - 使用 `python -c "import PyInstaller"` 检查是否已安装
   - 如果未安装，执行 `python -m pip install pyinstaller`

3. **清理之前的构建**:
   - 删除 `build\backend` 目录
   - 删除 `dist\backend` 目录
   - 删除 `backend\build` 目录
   - 删除 `backend\dist` 目录

4. **执行 PyInstaller**:
   - 进入 `backend` 目录
   - 执行: `python -m PyInstaller --clean --noconfirm pyinstaller.spec`
   - `--clean`: 清理临时文件
   - `--noconfirm`: 不询问确认，直接覆盖

5. **验证输出**:
   - 检查 `backend\dist\moke-backend.exe` 是否存在
   - 如果存在，复制到 `backend\moke-backend.exe`
   - 显示文件大小

**关键点**:
- Windows 上 PyInstaller 生成的可执行文件扩展名是 `.exe`
- 可执行文件需要复制到 `backend` 目录根目录，供 Electron 使用
- `pyinstaller.spec` 文件定义了打包的详细配置

**常见问题**:
- PyInstaller 打包失败: 检查 `pyinstaller.spec` 文件中的路径配置是否正确
- 缺少依赖: 确保虚拟环境中安装了所有必需的 Python 包
- 可执行文件过大: 这是正常的，因为包含了 Python 解释器和所有依赖

---

#### 3.3 准备 Playwright 浏览器

**脚本**: `build_electron_app.bat` (步骤 3.3)

**详细流程**:

1. **安装 Playwright 浏览器**:
   - 尝试在虚拟环境中安装:
     - 检查 `backend\venv\Scripts\activate.bat` 是否存在
     - 如果存在，激活虚拟环境
     - 执行: `playwright install chromium chromium-headless-shell`
     - 如果失败，尝试: `playwright install chromium`
   - 如果虚拟环境不存在，尝试全局安装:
     - `playwright install chromium chromium-headless-shell`
     - 或 `python -m playwright install chromium chromium-headless-shell`

2. **查找 Playwright 缓存目录**:
   - Windows 默认位置: `%LOCALAPPDATA%\ms-playwright`
   - 如果 `LOCALAPPDATA` 未定义，使用: `%USERPROFILE%\AppData\Local\ms-playwright`
   - 如果目录不存在，脚本会报错并退出

3. **复制浏览器文件**:
   - 创建 `backend\playwright-browsers` 目录
   - 查找所有 `chromium-*` 目录（如 `chromium-1200`）
   - 查找所有 `chromium_headless_shell-*` 目录（如 `chromium_headless_shell-1200`）
   - 使用 `xcopy /E /I /Y` 复制每个浏览器目录:
     - `/E`: 复制所有子目录，包括空目录
     - `/I`: 如果目标不存在，假设目标是目录
     - `/Y`: 覆盖已存在的文件时不提示

**关键点**:
- Playwright 浏览器文件很大（每个版本约 150-200MB），复制需要一些时间
- 需要复制所有找到的浏览器版本，以确保兼容性
- Windows 上使用 `xcopy` 而不是 `cp`（Linux/macOS 命令）

**常见问题**:
- Playwright 缓存目录不存在: 需要先运行 `playwright install chromium`
- 复制失败: 检查磁盘空间是否充足
- 权限问题: 确保有写入 `backend\playwright-browsers` 目录的权限

---

### 阶段 4: 构建前端

**脚本**: `build_electron_app.bat` (步骤 4)

**操作**:
1. 进入 `frontend` 目录
2. 执行 `npm run build`
3. 返回项目根目录

**关键点**:
- 前端构建会生成 `frontend\dist` 目录
- 构建过程会进行 TypeScript 编译和 Vite 打包
- 构建输出会被 Electron 打包到应用中

**常见问题**:
- TypeScript 编译错误: 检查 `frontend\src` 目录中的 TypeScript 代码
- 构建失败: 检查 `frontend\package.json` 中的依赖是否正确安装

---

### 阶段 5: 打包 Electron 应用

**脚本**: `build_electron_app.bat` (步骤 5)

**操作**:
1. **清理之前的构建**:
   - 删除 `release` 目录（如果存在）
   - 使用 `rmdir /s /q` 递归删除目录:
     - `/s`: 删除目录及其所有子目录和文件
     - `/q`: 安静模式，不询问确认

2. **执行 Electron Builder**:
   - 执行 `npm run build:electron`
   - 这会调用 `electron-builder`，根据 `package.json` 中的 `build` 配置进行打包

**Electron Builder 配置** (`package.json`):

```json
{
  "build": {
    "win": {
      "target": [
        {
          "target": "nsis",
          "arch": ["x64"]
        }
      ],
      "icon": "build/icon.ico"
    }
  }
}
```

**关键点**:
- Windows 目标格式是 `nsis`（Nullsoft Scriptable Install System）
- 需要 `build/icon.ico` 图标文件
- 输出目录是 `release`
- 最终会生成 `.exe` 安装程序

**打包过程**:
1. Electron Builder 会读取 `package.json` 中的配置
2. 将 `electron/**/*` 和 `frontend/dist/**/*` 打包到应用中
3. 将 `backend` 目录复制到 `extraResources`（资源目录）
4. 将 `frontend/dist` 复制到 `extraResources`
5. 生成 NSIS 安装程序

**输出文件**:
- `release/MoKe Setup 1.0.0.exe` - Windows 安装程序

**常见问题**:
- 图标文件不存在: 需要创建 `build/icon.ico` 文件（可以从 `icon.icns` 转换）
- 打包失败: 检查 `package.json` 中的配置是否正确
- 文件过大: 这是正常的，因为包含了 Electron 运行时、前端资源和后端可执行文件

---

## 关键文件说明

### 1. build_electron_app.bat

**作用**: Windows 平台主构建脚本，协调整个构建流程

**调用顺序**:
1. 检查环境
2. 安装依赖
3. 同步帮助文档
4. 调用 `build_backend.bat` 打包后端
5. 准备 Playwright 浏览器
6. 构建前端
7. 打包 Electron 应用

**关键命令**:
- `setlocal enabledelayedexpansion`: 启用延迟变量扩展
- `%~dp0`: 获取脚本所在目录
- `cd /d`: 切换目录（`/d` 允许切换到不同驱动器）

---

### 2. build_backend.bat

**作用**: 使用 PyInstaller 将 Python 后端打包为 Windows 可执行文件

**关键步骤**:
1. 激活虚拟环境
2. 检查/安装 PyInstaller
3. 清理旧构建
4. 执行 PyInstaller
5. 验证并复制可执行文件

**输出**:
- `backend/dist/moke-backend.exe` - PyInstaller 生成的可执行文件
- `backend/moke-backend.exe` - 复制到根目录的可执行文件（供 Electron 使用）

---

### 3. backend/start_backend_binary.bat

**作用**: 在打包后的应用中启动后端服务

**关键功能**:
1. **环境变量设置**:
   - `APP_RESOURCES`: 应用资源目录（由 Electron 设置）
   - `APP_DATA_DIR`: 应用数据目录（默认: `%USERPROFILE%\.moke`）
   - `PLAYWRIGHT_BROWSERS_PATH`: Playwright 浏览器路径

2. **端口检查**:
   - 使用 `netstat -aon` 查找占用 8765 端口的进程
   - 使用 `taskkill /F /PID` 强制关闭占用端口的进程

3. **启动后端**:
   - 查找 `moke-backend.exe` 可执行文件
   - 设置工作目录和环境变量
   - 启动后端进程并将输出重定向到日志文件

**日志文件**:
- `%APP_DATA_DIR%\logs\bootstrap.log` - 启动脚本日志
- `%APP_DATA_DIR%\logs\backend.log` - 后端服务日志

---

### 4. electron/main.js

**作用**: Electron 主进程代码，负责启动后端和前端

**Windows 平台适配**:

```javascript
// 平台检测
const isWindows = process.platform === 'win32';
const isMac = process.platform === 'darwin';

// 根据平台选择脚本
const binaryScriptPath = isWindows 
  ? path.join(backendDir, 'start_backend_binary.bat')
  : path.join(backendDir, 'start_backend_binary.sh');

// 根据平台选择启动方式
if (isWindows) {
  backendProcess = spawn(scriptPath, [], {
    shell: true  // Windows 需要 shell: true
  });
} else {
  backendProcess = spawn('bash', [scriptPath], []);
}
```

**关键点**:
- `process.platform` 在 Windows 上返回 `'win32'`
- Windows 上启动 `.bat` 文件需要 `shell: true`
- macOS/Linux 上使用 `bash` 执行 `.sh` 文件

---

## 平台差异对比

| 项目 | macOS | Windows |
|------|-------|---------|
| **脚本扩展名** | `.sh` | `.bat` |
| **可执行文件** | `moke-backend` | `moke-backend.exe` |
| **启动脚本** | `start_backend_binary.sh` | `start_backend_binary.bat` |
| **虚拟环境激活** | `source venv/bin/activate` | `call venv\Scripts\activate.bat` |
| **Playwright 缓存** | `~/Library/Caches/ms-playwright` | `%LOCALAPPDATA%\ms-playwright` |
| **路径分隔符** | `/` | `\` |
| **复制命令** | `cp -R` | `xcopy /E /I /Y` |
| **端口检查** | `lsof -ti:8765` | `netstat -aon \| findstr :8765` |
| **进程终止** | `kill -9` | `taskkill /F /PID` |
| **环境变量** | `$HOME` | `%USERPROFILE%` |

---

## 测试和调试指南

### 1. 逐步测试

建议按以下顺序逐步测试每个阶段：

1. **测试环境检查**:
   ```batch
   where node
   where npm
   where python
   ```

2. **测试依赖安装**:
   ```batch
   npm install
   cd frontend && npm install
   ```

3. **测试后端打包**:
   ```batch
   build_backend.bat
   ```
   检查 `backend\moke-backend.exe` 是否存在

4. **测试 Playwright 浏览器复制**:
   ```batch
   playwright install chromium chromium-headless-shell
   ```
   检查 `backend\playwright-browsers` 目录是否包含浏览器文件

5. **测试前端构建**:
   ```batch
   cd frontend && npm run build
   ```
   检查 `frontend\dist` 目录是否生成

6. **测试 Electron 打包**:
   ```batch
   npm run build:electron
   ```
   检查 `release` 目录是否生成安装程序

---

### 2. 常见错误和解决方案

#### 错误 1: Python 未找到

**症状**: `where python` 返回空

**解决方案**:
1. 确认 Python 已安装
2. 将 Python 安装目录添加到 PATH 环境变量
3. 重启命令行窗口

---

#### 错误 2: PyInstaller 打包失败

**症状**: `build_backend.bat` 执行失败

**解决方案**:
1. 检查虚拟环境是否正确激活
2. 检查 `pyinstaller.spec` 文件中的路径是否正确
3. 检查是否缺少 Python 依赖包
4. 查看 PyInstaller 的错误输出

---

#### 错误 3: Playwright 浏览器未找到

**症状**: `backend\playwright-browsers` 目录为空

**解决方案**:
1. 手动运行: `playwright install chromium chromium-headless-shell`
2. 检查 `%LOCALAPPDATA%\ms-playwright` 目录是否存在
3. 检查网络连接（浏览器需要从网络下载）

---

#### 错误 4: Electron Builder 打包失败

**症状**: `npm run build:electron` 失败

**解决方案**:
1. 检查 `build/icon.ico` 文件是否存在
2. 检查 `package.json` 中的 `build.win` 配置是否正确
3. 检查磁盘空间是否充足
4. 查看 Electron Builder 的错误输出

---

#### 错误 5: 后端启动失败

**症状**: 应用启动后后端服务无法启动

**解决方案**:
1. 检查 `backend\moke-backend.exe` 是否存在
2. 检查 `backend\start_backend_binary.bat` 是否存在
3. 查看 `%USERPROFILE%\.moke\logs\bootstrap.log` 日志文件
4. 检查端口 8765 是否被占用

---

### 3. 日志文件位置

**构建日志**:
- 构建过程中的输出会直接显示在命令行窗口

**运行时日志**:
- `%USERPROFILE%\.moke\logs\bootstrap.log` - 后端启动脚本日志
- `%USERPROFILE%\.moke\logs\backend.log` - 后端服务日志

**Electron 日志**:
- Electron 主进程日志会输出到命令行（如果从命令行启动）
- 渲染进程日志可以在开发者工具中查看

---

## 图标文件准备

### 创建 icon.ico

Windows 应用需要 `build/icon.ico` 文件。如果只有 `icon.icns`（macOS 格式），需要转换：

**方法 1: 使用在线工具**
1. 访问在线图标转换工具（如 https://convertio.co/icns-ico/）
2. 上传 `build/icon.icns` 文件
3. 下载转换后的 `icon.ico` 文件
4. 保存到 `build/icon.ico`

**方法 2: 使用 ImageMagick**
```batch
magick convert build/icon.icns build/icon.ico
```

**方法 3: 使用 Python PIL/Pillow**
```python
from PIL import Image
img = Image.open('build/icon.icns')
img.save('build/icon.ico', format='ICO')
```

**图标要求**:
- 格式: `.ico`
- 建议尺寸: 256x256 或 512x512 像素
- 位置: `build/icon.ico`

---

## 验证清单

在 Windows 平台上测试打包脚本时，请按以下清单验证：

- [ ] 环境检查通过（Node.js, npm, Python）
- [ ] 依赖安装成功
- [ ] 帮助文档同步成功
- [ ] 后端打包成功（生成 `moke-backend.exe`）
- [ ] Playwright 浏览器复制成功
- [ ] 前端构建成功（生成 `frontend/dist`）
- [ ] Electron 打包成功（生成 `release` 目录）
- [ ] 安装程序可以正常安装
- [ ] 安装后的应用可以正常启动
- [ ] 后端服务可以正常启动
- [ ] 前端界面可以正常显示
- [ ] Playwright 浏览器可以正常使用

---

## 注意事项

1. **路径问题**: Windows 使用反斜杠 `\` 作为路径分隔符，批处理脚本中需要注意转义
2. **权限问题**: 某些操作可能需要管理员权限
3. **编码问题**: 批处理脚本应使用 UTF-8 编码，避免中文乱码
4. **虚拟环境**: 建议始终在虚拟环境中运行 Python 相关操作
5. **磁盘空间**: 构建过程需要大量磁盘空间（至少 2GB）
6. **网络连接**: Playwright 浏览器安装需要网络连接

---

## 参考文件

- `build_electron_app.sh` - macOS 版本构建脚本（参考）
- `build_backend.sh` - macOS 版本后端打包脚本（参考）
- `backend/start_backend_binary.sh` - macOS 版本后端启动脚本（参考）
- `package.json` - Electron Builder 配置
- `backend/pyinstaller.spec` - PyInstaller 配置文件

---

## 更新日志

- 2026-01-25: 初始版本，创建 Windows 构建脚本和文档

---

## 联系和支持

如果在测试和修正过程中遇到问题，请：
1. 查看本文档的"常见错误和解决方案"部分
2. 检查日志文件获取详细错误信息
3. 对比 macOS 版本的脚本找出差异
4. 参考 Electron Builder 和 PyInstaller 官方文档
