"""
常量定义文件

注意：配置相关常量已移动到app.data.config中
"""

from enum import Enum

from app.core.config import DEFAULT_CONFIG_PATH


class SYS_TYPE(Enum):
    """系统类型枚举"""
    WIN_64 = "win64"
    MAC_INTEL = "mac_intel"
    MAC_SILICON = "mac_silicon"

POSTER_WORD_COUNT = 150

class DEFAULT_TASK_TYPE(Enum):
    """任务类型枚举"""
    XHS_TYPE = "xhs_type"

# ==============================================
# 新的任务数据目录结构（按用户隔离）
# ==============================================
# 任务数据基础路径
TASK_DATA_BASE_PATH = './app/data/task_data/'

# 用户子目录名称
USER_COOKIES_DIR = 'cookies'
USER_IMAGES_DIR = 'images'
USER_NOTES_DIR = 'notes'
USER_SOURCES_DIR = 'sources'

# ==============================================
# 向后兼容的旧路径（已废弃，将在未来版本移除）
# ==============================================
DEFAULT_KNOWLEDGE_PATH = './app/data/task_data/sources/'  # 已废弃
DEFAULT_IMAGE_PATH = './app/data/task_data/images/'       # 已废弃
DEFAULT_NOTES_PATH = './app/data/task_data/notes/'        # 已废弃

# cookie地址配置
COOKIE_SOURCE_PATH = './xhs_mcp/'
COOKIE_TARGET_PATH = './app/data/task_data/cookies/'      # 已废弃
