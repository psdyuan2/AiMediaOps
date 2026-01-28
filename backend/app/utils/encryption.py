"""
简单的加密工具封装

用于对本地配置（例如注册码配置）进行加密存储。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from cryptography.fernet import Fernet

from app.core.logger import logger


_FERNET: Fernet | None = None


def _get_key_file() -> Path:
    """
    获取本地密钥文件路径（用于在未设置环境变量时持久化密钥）。
    
    优先使用 APP_DATA_DIR（用户数据目录），确保在打包环境中也能持久化。
    """
    # 优先使用 APP_DATA_DIR 环境变量（由启动脚本设置）
    app_data_dir = os.getenv("APP_DATA_DIR")
    if app_data_dir:
        key_path = Path(app_data_dir) / "license.key"
        # 确保目录存在
        key_path.parent.mkdir(parents=True, exist_ok=True)
        return key_path
    
    # 回退到项目根目录（开发环境）
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "license.key"


def _load_or_create_key() -> bytes:
    """
    从环境变量或本地文件加载密钥。

    优先级：
    1. 环境变量 LICENSE_SECRET_KEY（推荐）
    2. 本地文件 license.key（如不存在则自动生成）
    """
    env_key = os.getenv("LICENSE_SECRET_KEY")
    if env_key:
        try:
            # 兼容直接存放 Fernet key 或普通字符串
            # 如果是 44 字节的 urlsafe_b64，则直接使用；否则对其进行派生
            key_bytes = env_key.encode("utf-8")
            if len(key_bytes) == 44:
                return key_bytes
        except Exception:
            logger.warning("LICENSE_SECRET_KEY 解析失败，将使用本地密钥文件。")

    key_file = _get_key_file()
    if key_file.exists():
        try:
            data = key_file.read_bytes().strip()
            if data:
                return data
        except Exception as e:
            logger.error(f"读取本地密钥文件失败: {e}")

    # 生成新的密钥并写入文件
    key = Fernet.generate_key()
    try:
        key_file.write_bytes(key)
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            # 某些系统可能不支持 chmod，忽略即可
            pass
        logger.info(f"已生成新的加密密钥文件: {key_file}")
    except Exception as e:
        logger.error(f"写入本地密钥文件失败: {e}")

    return key


def get_fernet() -> Fernet:
    """
    获取全局 Fernet 实例（单例）。
    """
    global _FERNET
    if _FERNET is None:
        key = _load_or_create_key()
        _FERNET = Fernet(key)
    return _FERNET


def encrypt_dict(data: Dict[str, Any]) -> bytes:
    """
    加密字典数据，返回字节串。
    """
    f = get_fernet()
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return f.encrypt(raw)


def decrypt_dict(token: bytes) -> Dict[str, Any]:
    """
    解密字节串为字典。
    """
    f = get_fernet()
    raw = f.decrypt(token)
    return json.loads(raw.decode("utf-8"))

