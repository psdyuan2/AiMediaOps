"""
常量定义文件

注意：配置相关常量已移动到app.data.config中
"""

from enum import Enum
import os
from app.core.config import DEFAULT_CONFIG_PATH, APP_DATA_DIR, RESOURCE_DIR


class SYS_TYPE(Enum):
    """系统类型枚举"""
    WIN_64 = "win64"
    MAC_INTEL = "mac_intel"
    MAC_SILICON = "mac_silicon"
    def __str__(self):
        return self.value

POSTER_WORD_COUNT = 150

class DEFAULT_TASK_TYPE(Enum):
    """任务类型枚举"""
    XHS_TYPE = "xhs_type"
    def __str__(self):
        return self.value

# ==============================================
# 新的任务数据目录结构（按用户隔离）
# ==============================================
# 任务数据基础路径 - 迁移到用户数据目录
TASK_DATA_BASE_PATH = str(APP_DATA_DIR / "task_data")
# 任务默认执行间隔时间
TASK_INTERVAL_TIME = 60*60

# 用户子目录名称
USER_COOKIES_DIR = 'cookies'
USER_IMAGES_DIR = 'images'
USER_NOTES_DIR = 'notes'
USER_SOURCES_DIR = 'sources'

# ==============================================
# 向后兼容的旧路径（已废弃，将在未来版本移除）
# ==============================================
# 保持兼容性，但也指向 APP_DATA_DIR
DEFAULT_KNOWLEDGE_PATH = str(APP_DATA_DIR / "task_data" / "sources")
DEFAULT_IMAGE_PATH = str(APP_DATA_DIR / "task_data" / "images")
DEFAULT_NOTES_PATH = str(APP_DATA_DIR / "task_data" / "notes")

# cookie地址配置
# 源路径（可能包含默认配置）指向资源目录
COOKIE_SOURCE_PATH = str(RESOURCE_DIR / "app" / "xhs_mcp")
# 目标路径指向数据目录
COOKIE_TARGET_PATH = str(APP_DATA_DIR / "task_data" / "cookies")

# ==============================================
# 日志类型枚举 (LogBindType)
# ==============================================
class LogBindType(str, Enum):
    """日志绑定类型枚举
    
    用于区分不同类型的日志，不同类型的日志会保存到不同的日志文件中。
    前端只展示 task_log 类型的日志。
    """
    TASK_LOG = "task_log"      # 任务执行日志（前端展示）
    SYSTEM_LOG = "system_log"   # 系统日志
    ACCESS_LOG = "access_log"   # 访问日志
    ERROR_LOG = "error_log"     # 错误日志
    
    def __str__(self):
        return self.value


class TaskMode(str, Enum):
    """任务执行模式枚举"""
    STANDARD = "standard"        # 标准模式：互动 + 发布
    INTERACTION = "interaction"  # 互动模式：仅互动
    PUBLISH = "publish"          # 发布模式：仅发布
    
    def __str__(self):
        return self.value
