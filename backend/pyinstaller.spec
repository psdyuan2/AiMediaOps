# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# PyInstaller 需要的变量
block_cipher = None

# 获取 spec 文件所在目录（backend 目录）
# SPECPATH 在 PyInstaller 中可能指向目录或文件，需要处理两种情况
if 'SPECPATH' in globals():
    spec_path = Path(SPECPATH)
    # 如果 SPECPATH 是文件路径，取其父目录
    if spec_path.suffix == '.spec' or spec_path.name == 'pyinstaller.spec':
        backend_dir = spec_path.parent
    # 如果 SPECPATH 是目录路径，直接使用
    elif spec_path.is_dir():
        backend_dir = spec_path
    else:
        # 默认假设是目录
        backend_dir = spec_path
else:
    # 如果 SPECPATH 不存在，从当前工作目录推断
    cwd = Path.cwd()
    if (cwd / 'pyinstaller.spec').exists():
        backend_dir = cwd
    elif (cwd.parent / 'backend' / 'pyinstaller.spec').exists():
        backend_dir = cwd.parent / 'backend'
    else:
        backend_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()

app_dir = backend_dir / 'app'
root_dir = backend_dir.parent
main_py = backend_dir / 'main.py'

# 检查文件是否存在
if not main_py.exists():
    raise FileNotFoundError(f"main.py not found at {main_py}. Current directory: {Path.cwd()}, backend_dir: {backend_dir}, SPECPATH: {SPECPATH if 'SPECPATH' in globals() else 'N/A'}")

# 收集所有需要包含的数据文件
datas = [
    # 包含 app 目录下的所有 Python 文件和数据文件
    (str(app_dir / 'prompts'), 'app/prompts'),
    (str(app_dir / 'api' / 'static'), 'app/api/static'),
    # 包含 app/xhs_mcp 目录（现在包含 Python 代码和二进制文件）
    (str(backend_dir / 'app' / 'xhs_mcp'), 'app/xhs_mcp'),
    # 包含 .env 文件（如果存在）
    (str(root_dir / '.env'), '.'),
    # 包含 docs 目录
    (str(root_dir / 'docs'), 'docs'),
]

# 收集隐藏导入（PyInstaller 可能无法自动检测的模块）
hiddenimports = [
    'uvicorn',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.logging',
    'fastapi',
    'starlette',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.middleware.base',
    'starlette.exceptions',
    'pydantic',
    'pydantic.json',
    'pydantic.types',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    'anyio._backends._trio',
    'anyio._core',
    'anyio._core._eventloop',
    'anyio._core._synchronization',
    'httptools',
    'websockets',
    'h11',
    'click',
    'loguru',
    'diskcache',
    'playwright',
    'playwright.async_api',
    'langchain',
    'langchain_openai',
    'mcp',
    'cryptography',
    'jinja2',
    'yaml',
    'aiofiles',
    'aiohttp',
    'psutil',
    'app.utils.mcp_service_manager',  # 显式添加模块
]

a = Analysis(
    [str(main_py)],
    pathex=[str(backend_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='moke-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台，便于调试
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
