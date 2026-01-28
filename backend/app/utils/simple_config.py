"""
极简配置管理工具
只支持简单的KEY=VALUE格式，就像用户要求的那样
"""

import os
from typing import Any, Dict, Optional


def get(key: str, default: Any = None) -> str:
    """获取配置值"""
    return os.getenv(key, default)


def get_int(key: str, default: int = 0) -> int:
    """获取整数配置值"""
    value = os.getenv(key, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def get_bool(key: str, default: bool = False) -> bool:
    """获取布尔配置值"""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def get_float(key: str, default: float = 0.0) -> float:
    """获取浮点数配置值"""
    value = os.getenv(key, str(default))
    try:
        return float(value)
    except ValueError:
        return default


def get_list(key: str, default: list = None, separator: str = ',') -> list:
    """获取列表配置值"""
    value = os.getenv(key, str(default))
    if value and value != str(default):
        return [item.strip() for item in value.split(separator)]
    return default or []


def get_all(prefix: str = '') -> Dict[str, str]:
    """获取指定前缀的所有配置"""
    config = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            config[key] = value
    return config


def print_config(prefix: str = '') -> None:
    """打印配置（用于调试）"""
    config = get_all(prefix)
    if config:
        print(f"🔧 {prefix} 配置:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        print()
    else:
        print(f"🔧 没有前缀为 '{prefix}' 的配置")


def set_env(key: str, value: Any) -> None:
    """设置环境变量（用于前端修改）"""
    os.environ[key] = str(value)
    return None