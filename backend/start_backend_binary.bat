@echo off
REM 启动 PyInstaller 打包的后端可执行文件 (Windows)

setlocal enabledelayedexpansion

REM 获取脚本所在目录（应用资源目录）
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%"

REM 从环境变量获取资源目录（由 Electron 设置）
if not defined APP_RESOURCES set "APP_RESOURCES=%BACKEND_DIR%"
REM 运行时数据目录（日志、数据库等）
if not defined APP_DATA_DIR set "APP_DATA_DIR=%USERPROFILE%\.moke"
set "APP_DATA_DIR=%APP_DATA_DIR%"

REM 创建应用数据目录（用于日志、数据库等）
if not exist "%APP_DATA_DIR%\logs" mkdir "%APP_DATA_DIR%\logs"
set "BOOTSTRAP_LOG=%APP_DATA_DIR%\logs\bootstrap.log"

REM 记录脚本自身的输出，便于排障
echo ============================================================ >> "%BOOTSTRAP_LOG%"
echo %date% %time% MoKe backend bootstrap (Binary) >> "%BOOTSTRAP_LOG%"
echo APP_RESOURCES=%APP_RESOURCES% >> "%BOOTSTRAP_LOG%"
echo APP_DATA_DIR=%APP_DATA_DIR% >> "%BOOTSTRAP_LOG%"

REM 函数：检查并关闭占用指定端口的进程
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    echo ⚠️  发现端口 8765 被进程 %%a 占用，正在关闭... >> "%BOOTSTRAP_LOG%"
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 1 >nul
)

REM 设置 Playwright 浏览器路径
REM 优先使用 Electron 传递的环境变量
if defined PLAYWRIGHT_BROWSERS_PATH (
    set "PLAYWRIGHT_BROWSERS_PATH=%PLAYWRIGHT_BROWSERS_PATH%"
    echo ✅ 使用 Electron 传递的 Chromium 路径: %PLAYWRIGHT_BROWSERS_PATH% >> "%BOOTSTRAP_LOG%"
) else if exist "%APP_RESOURCES%\backend\playwright-browsers" (
    set "PLAYWRIGHT_BROWSERS_PATH=%APP_RESOURCES%\backend\playwright-browsers"
    echo ✅ 使用打包的 Chromium (backend): %PLAYWRIGHT_BROWSERS_PATH% >> "%BOOTSTRAP_LOG%"
) else if exist "%APP_RESOURCES%\playwright-browsers" (
    set "PLAYWRIGHT_BROWSERS_PATH=%APP_RESOURCES%\playwright-browsers"
    echo ✅ 使用打包的 Chromium (root): %PLAYWRIGHT_BROWSERS_PATH% >> "%BOOTSTRAP_LOG%"
) else (
    REM 开发环境回退到默认路径
    if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
    set "PLAYWRIGHT_BROWSERS_PATH=%LOCALAPPDATA%\ms-playwright"
    echo ⚠️  使用默认 Chromium 路径: %PLAYWRIGHT_BROWSERS_PATH% >> "%BOOTSTRAP_LOG%"
)

REM 查找可执行文件
set "BINARY_PATH=%BACKEND_DIR%\moke-backend.exe"
if not exist "%BINARY_PATH%" (
    REM 尝试在 dist 目录中查找
    set "BINARY_PATH=%BACKEND_DIR%\dist\moke-backend.exe"
)

if not exist "%BINARY_PATH%" (
    echo ❌ 错误: 未找到后端可执行文件 >> "%BOOTSTRAP_LOG%"
    echo    查找路径: %BACKEND_DIR%\moke-backend.exe >> "%BOOTSTRAP_LOG%"
    echo    查找路径: %BACKEND_DIR%\dist\moke-backend.exe >> "%BOOTSTRAP_LOG%"
    exit /b 1
)

REM 设置工作目录为后端目录
cd /d "%BACKEND_DIR%"

REM 设置环境变量
set "PYTHONPATH=%BACKEND_DIR%;%PYTHONPATH%"
set "API_HOST=127.0.0.1"
set "API_PORT=8765"
set "API_LOG_LEVEL=info"

REM 启动后端服务
echo 🚀 启动 MoKe 后端服务（二进制版本）... >> "%BOOTSTRAP_LOG%"
echo    工作目录: %BACKEND_DIR% >> "%BOOTSTRAP_LOG%"
echo    可执行文件: %BINARY_PATH% >> "%BOOTSTRAP_LOG%"
echo    端口: %API_PORT% >> "%BOOTSTRAP_LOG%"
echo    日志目录: %APP_DATA_DIR%\logs >> "%BOOTSTRAP_LOG%"

REM 将输出重定向到日志文件
set "LOG_FILE=%APP_DATA_DIR%\logs\backend.log"
"%BINARY_PATH%" >> "%LOG_FILE%" 2>&1
