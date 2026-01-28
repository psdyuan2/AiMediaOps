@echo off
REM Electron 应用一键打包脚本 (Windows)

setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo ========================================
echo   MoKe Electron 应用打包脚本 (Windows)
echo ========================================
echo.

REM 步骤 1: 检查环境
echo [步骤 1] 检查环境
echo ----------------------------------------

REM 检查 Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Node.js，请先安装 Node.js
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo ✅ Node.js: %NODE_VERSION%

REM 检查 npm
where npm >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 npm
    exit /b 1
)
for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo ✅ npm: %NPM_VERSION%

REM 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python 3
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ Python: %PYTHON_VERSION%

REM 步骤 2: 安装依赖
echo.
echo [步骤 2] 安装依赖
echo ----------------------------------------

if not exist "node_modules" (
    echo 安装 Electron 依赖...
    call npm install
) else (
    echo 检查 Electron 依赖...
    call npm install
)

if not exist "frontend\node_modules" (
    echo 安装前端依赖...
    cd frontend
    call npm install
    cd ..
) else (
    echo 检查前端依赖...
    cd frontend
    call npm install
    cd ..
)

REM 步骤 3: 准备后端环境
echo.
echo [步骤 3] 准备后端环境
echo ----------------------------------------

set "BACKEND_DIR=%PROJECT_ROOT%backend"

REM 步骤 3.1: 同步帮助文档
echo.
echo [步骤 3.1] 同步帮助文档
echo ----------------------------------------

if exist "%PROJECT_ROOT%frontend\public\help_guide.md" (
    echo 同步帮助文档到 docs 目录...
    copy /Y "%PROJECT_ROOT%frontend\public\help_guide.md" "%PROJECT_ROOT%docs\help_guide.md" >nul
    echo ✅ 帮助文档已同步
) else (
    echo ⚠️  未找到 frontend\public\help_guide.md
)

REM 步骤 3.2: 使用 PyInstaller 打包后端
echo.
echo [步骤 3.2] 使用 PyInstaller 打包后端
echo ----------------------------------------

if exist "%PROJECT_ROOT%build_backend.bat" (
    echo 调用 build_backend.bat 进行打包...
    call "%PROJECT_ROOT%build_backend.bat"
    
    REM 检查打包结果
    if not exist "%BACKEND_DIR%\moke-backend.exe" (
        echo ❌ 后端打包失败：未找到可执行文件
        exit /b 1
    )
) else (
    echo ❌ 未找到 build_backend.bat 脚本
    exit /b 1
)

cd /d "%PROJECT_ROOT%"

REM 步骤 3.3: 准备 Playwright 浏览器
echo.
echo [步骤 3.3] 准备 Playwright 浏览器
echo ----------------------------------------

REM 尝试在虚拟环境中安装/更新浏览器
if exist "%BACKEND_DIR%\venv\Scripts\activate.bat" (
    call "%BACKEND_DIR%\venv\Scripts\activate.bat"
    echo 在虚拟环境中运行 playwright install chromium...
    playwright install chromium chromium-headless-shell || playwright install chromium
    call deactivate
) else if exist "%BACKEND_DIR%\.venv\Scripts\activate.bat" (
    call "%BACKEND_DIR%\.venv\Scripts\activate.bat"
    echo 在虚拟环境中运行 playwright install chromium...
    playwright install chromium chromium-headless-shell || playwright install chromium
    call deactivate
) else (
    echo 尝试使用全局 playwright 安装...
    playwright install chromium chromium-headless-shell || playwright install chromium || python -m playwright install chromium chromium-headless-shell || python -m playwright install chromium || echo 无法安装 Playwright 浏览器
)

REM 查找并复制 Chromium
REM Windows 上浏览器通常安装在 %LOCALAPPDATA%\ms-playwright
echo 搜索 Playwright 浏览器...

set "PLAYWRIGHT_CACHE="
if defined LOCALAPPDATA (
    set "PLAYWRIGHT_CACHE=%LOCALAPPDATA%\ms-playwright"
) else (
    set "PLAYWRIGHT_CACHE=%USERPROFILE%\AppData\Local\ms-playwright"
)

if not exist "%PLAYWRIGHT_CACHE%" (
    echo ❌ 未找到 Playwright 缓存目录！
    echo 请先运行: playwright install chromium
    exit /b 1
)

echo 找到 Playwright 缓存目录: %PLAYWRIGHT_CACHE%

if not exist "%BACKEND_DIR%\playwright-browsers" mkdir "%BACKEND_DIR%\playwright-browsers"

REM 查找所有 chromium 相关目录
set "CHROMIUM_FOUND=0"
for /d %%d in ("%PLAYWRIGHT_CACHE%\chromium-*") do (
    set "CHROMIUM_FOUND=1"
    set "DIR_NAME=%%~nxd"
    echo 找到 Chromium 浏览器: %DIR_NAME%
    
    REM 移除旧的（如果存在）
    if exist "%BACKEND_DIR%\playwright-browsers\%DIR_NAME%" (
        rmdir /s /q "%BACKEND_DIR%\playwright-browsers\%DIR_NAME%"
    )
    
    echo 复制 %DIR_NAME% 到: %BACKEND_DIR%\playwright-browsers\%DIR_NAME%
    xcopy /E /I /Y "%%d" "%BACKEND_DIR%\playwright-browsers\%DIR_NAME%\" >nul
)

for /d %%d in ("%PLAYWRIGHT_CACHE%\chromium_headless_shell-*") do (
    set "CHROMIUM_FOUND=1"
    set "DIR_NAME=%%~nxd"
    echo 找到 Chromium Headless Shell: %DIR_NAME%
    
    REM 移除旧的（如果存在）
    if exist "%BACKEND_DIR%\playwright-browsers\%DIR_NAME%" (
        rmdir /s /q "%BACKEND_DIR%\playwright-browsers\%DIR_NAME%"
    )
    
    echo 复制 %DIR_NAME% 到: %BACKEND_DIR%\playwright-browsers\%DIR_NAME%
    xcopy /E /I /Y "%%d" "%BACKEND_DIR%\playwright-browsers\%DIR_NAME%\" >nul
)

if "%CHROMIUM_FOUND%"=="1" (
    echo ✅ 已复制所有 Chromium 浏览器
) else (
    echo ❌ 未找到 Playwright Chromium 浏览器！应用可能无法正常执行爬虫任务。
    echo 请手动运行: cd backend ^&^& venv\Scripts\activate ^&^& playwright install chromium chromium-headless-shell
)

echo ✅ 后端环境准备完成
echo.

REM 步骤 4: 构建前端
echo [步骤 4] 构建前端
echo ----------------------------------------
cd /d "%PROJECT_ROOT%frontend"
call npm run build
cd /d "%PROJECT_ROOT%"
echo ✅ 前端构建完成
echo.

REM 步骤 5: 打包 Electron 应用
echo [步骤 5] 打包 Electron 应用
echo ----------------------------------------
echo 清理之前的构建产物...

REM 清理构建目录
if exist "release" rmdir /s /q "release"

echo 开始 Electron 打包（这可能需要较长时间）...
call npm run build:electron

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo 安装包位置: release\
