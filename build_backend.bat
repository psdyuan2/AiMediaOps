@echo off
REM 使用 PyInstaller 打包后端服务为可执行文件 (Windows)

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "BUILD_DIR=%SCRIPT_DIR%build"
set "DIST_DIR=%SCRIPT_DIR%dist"

echo ============================================================
echo 开始打包后端服务...
echo 后端目录: %BACKEND_DIR%
echo 构建目录: %BUILD_DIR%
echo 输出目录: %DIST_DIR%
echo ============================================================

REM 自动激活虚拟环境
if not defined VIRTUAL_ENV (
    if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
        echo 🔧 激活虚拟环境: %SCRIPT_DIR%venv
        call "%SCRIPT_DIR%venv\Scripts\activate.bat"
    ) else if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
        echo 🔧 激活虚拟环境: %SCRIPT_DIR%.venv
        call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
    )
)

REM 检查是否在虚拟环境中
if not defined VIRTUAL_ENV (
    echo ⚠️  警告: 未检测到虚拟环境，建议在虚拟环境中运行此脚本
    echo    如果使用系统 Python，请确保已安装所有依赖
)

REM 检查 PyInstaller 是否已安装
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 📦 安装 PyInstaller...
    python -m pip install pyinstaller
)

REM 进入后端目录
cd /d "%BACKEND_DIR%"

REM 清理之前的构建
echo 🧹 清理之前的构建...
if exist "%BUILD_DIR%\backend" rmdir /s /q "%BUILD_DIR%\backend"
if exist "%DIST_DIR%\backend" rmdir /s /q "%DIST_DIR%\backend"
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM 运行 PyInstaller（从 backend 目录运行）
echo 🔨 开始打包...
cd /d "%BACKEND_DIR%"
python -m PyInstaller --clean --noconfirm pyinstaller.spec

REM 检查输出文件
set "EXE_PATH=%BACKEND_DIR%\dist\moke-backend.exe"
if exist "%EXE_PATH%" (
    echo ✅ 打包成功！
    echo 可执行文件位置: %EXE_PATH%
    
    REM 显示文件大小
    for %%A in ("%EXE_PATH%") do set "FILE_SIZE=%%~zA"
    echo 文件大小: %FILE_SIZE% 字节
    
    REM 复制可执行文件到 backend 目录根目录（供 Electron 使用）
    copy /Y "%EXE_PATH%" "%BACKEND_DIR%\moke-backend.exe" >nul
    echo ✅ 可执行文件已复制到: %BACKEND_DIR%\moke-backend.exe
) else (
    echo ❌ 打包失败：未找到可执行文件
    exit /b 1
)

echo.
echo ============================================================
echo 打包完成！
echo 可执行文件: %EXE_PATH%
echo ============================================================
