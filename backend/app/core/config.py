"""
Configuration Manager Module

This module provides centralized configuration management for the context storage
and agent system. Supports hot-reloading, validation, and environment-specific
settings.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
import logging

# Base paths
def get_app_data_dir() -> Path:
    """获取应用数据目录（可写）"""
    env_path = os.getenv("APP_DATA_DIR")
    if env_path:
        path = Path(env_path)
    else:
        path = Path.home() / ".moke"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_resource_dir() -> Path:
    """获取应用资源目录（只读）"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    else:
        # backend/app/core/config.py -> backend/
        return Path(__file__).resolve().parent.parent.parent

APP_DATA_DIR = get_app_data_dir()
RESOURCE_DIR = get_resource_dir()

# 配置文件路径
# 优先使用环境变量
# 其次使用用户目录下的配置
# 最后使用打包的默认配置
ENV_CONFIG_PATH = os.getenv("CONTEXT_STORAGE_CONFIG_PATH", "")
USER_CONFIG_PATH = APP_DATA_DIR / "config" / "context_storage_config.yaml"
DEFAULT_CONFIG_PATH = RESOURCE_DIR / "config" / "context_storage_config.yaml"

# 日志器
logger = logging.getLogger(__name__)


class DatabaseType(str, Enum):
    """数据库类型枚举"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class NamingConvention(str, Enum):
    """文件命名策略枚举"""
    TIMESTAMP_ENGLISH = "timestamp_english_summary"
    TIMESTAMP_UUID = "timestamp_uuid"
    TIMESTAMP_NUMBERED = "timestamp_numbered"


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SyncMode(str, Enum):
    """SQLite同步模式枚举"""
    OFF = "OFF"
    NORMAL = "NORMAL"
    FULL = "FULL"


class JournalMode(str, Enum):
    """SQLite日志模式枚举"""
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"
    PERSIST = "PERSIST"
    MEMORY = "MEMORY"
    WAL = "WAL"
    OFF = "OFF"


class BackupSchedule(str, Enum):
    """备份频率枚举"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SearchType(str, Enum):
    """搜索类型枚举"""
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    SUMMARY = "summary"


class SQLiteConfig(BaseModel):
    """SQLite特定配置"""
    timeout: float = Field(default=30.0, ge=0)
    check_same_thread: bool = True
    isolation_level: Optional[str] = None  # None for autocommit mode
    sync_mode: SyncMode = SyncMode.NORMAL
    journal_mode: JournalMode = JournalMode.WAL
    cache_size: int = Field(default=-2000, description="Negative for KB, positive for pages")


class SecurityConfig(BaseModel):
    """安全配置"""
    encryption_enabled: bool = False
    encryption_key: Optional[str] = None
    access_control_enabled: bool = False
    allowed_users: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=list)


class MonitoringConfig(BaseModel):
    """监控和日志配置"""
    log_level: LogLevel = LogLevel.INFO
    log_path: Optional[str] = "logs/context_storage.log"
    max_file_size_mb: int = Field(default=10, ge=1)
    retain_files: int = Field(default=5, ge=1)
    detailed_operations: bool = False


class PerformanceConfig(BaseModel):
    """性能配置"""
    cache_enabled: bool = True
    max_memory_mb: int = Field(default=100, ge=10)
    cache_ttl_seconds: int = Field(default=300, ge=0)
    concurrent_searches: int = Field(default=5, ge=1)
    search_timeout: float = Field(default=10.0, ge=0.1)


class SearchConfig(BaseModel):
    """检索配置"""
    default_search_type: SearchType = SearchType.HYBRID
    keyword_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    time_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    max_results: int = Field(default=10, ge=1)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


class AgentConfig(BaseModel):
    """智能体交互配置"""
    default_time_window: str = "24h"  # e.g. "24h", "7d"
    default_search_type: str = "summary"
    default_max_blocks: int = 5
    auto_expand_window: bool = True
    relevance_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class StorageConfig(BaseModel):
    """存储核心配置"""
    root_dir: str = Field(default="context_storage", min_length=1)
    max_block_size: int = Field(default=1000, ge=100)
    max_time_interval: int = Field(default=3600, ge=60)
    db_type: DatabaseType = DatabaseType.SQLITE
    db_path: str = "database/context_blocks.db"
    backup_enabled: bool = True
    backup_schedule: BackupSchedule = BackupSchedule.DAILY
    backup_retention_days: int = Field(default=30, ge=1)
    
    # 子配置
    naming: Dict[str, Any] = Field(default_factory=lambda: {
        "convention": NamingConvention.TIMESTAMP_ENGLISH,
        "max_words": 5,
        "use_llm": True
    })
    
    sqlite: SQLiteConfig = Field(default_factory=SQLiteConfig)


class ContextStorageConfig(BaseModel):
    """根配置模型"""
    storage: StorageConfig = Field(default_factory=StorageConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """初始化配置管理器"""
        # Determine config path priority:
        # 1. Explicit argument
        # 2. Environment variable
        # 3. User data directory
        # 4. Default resource directory
        path_to_use = config_path or ENV_CONFIG_PATH
        if not path_to_use:
            if USER_CONFIG_PATH.exists():
                path_to_use = USER_CONFIG_PATH
            else:
                path_to_use = DEFAULT_CONFIG_PATH
        
        self.config_path = Path(path_to_use)
        self.config: ContextStorageConfig = ContextStorageConfig()
        self.raw_config: Dict = {}
        self.last_loaded: float = 0
        
        # 初始加载
        self.load_config()
    
    def load_config(self) -> ContextStorageConfig:
        """加载配置"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            return self.config
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
                
            if not config_dict:
                logger.warning("Config file is empty, using defaults")
                return self.config
                
            self.raw_config = config_dict
            
            # 基础环境覆盖
            env = self.get_environment()
            if env in config_dict:
                logger.info(f"Applying environment specific config for: {env}")
                env_config = config_dict[env]
                # 这里可以做深层合并，简化起见直接更新顶层
                self._deep_update(config_dict, env_config)
            
            # 转换为模型并验证
            self.config = ContextStorageConfig(**config_dict)
            self.last_loaded = os.path.getmtime(self.config_path)
            
            logger.info("Configuration loaded successfully")
            return self.config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # 出错时保留旧配置或默认配置
            return self.config
    
    def reload_config(self) -> bool:
        """检查并重载配置"""
        if not self.config_path.exists():
            return False
            
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime > self.last_loaded:
                logger.info("Config file changed, reloading...")
                self.load_config()
                return True
            return False
        except Exception:
            return False
    
    def get_config(self) -> ContextStorageConfig:
        """获取当前配置"""
        return self.config
    
    def get_environment(self) -> str:
        """获取当前环境名称"""
        return os.getenv("APP_ENV", "development")
    
    def get_environment_config(self) -> Dict[str, Any]:
        """获取当前环境的特定配置字典"""
        env = self.get_environment()
        return self.raw_config.get(env, {})

    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """递归更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳字符串"""
        from datetime import datetime
        return datetime.now().isoformat()

    def __str__(self) -> str:
        """字符串表示"""
        return f"ConfigManager(env={self.get_environment()}, config={self.config_path})"


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[Union[str, Path]] = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def get_config() -> ContextStorageConfig:
    """获取当前环境配置的便捷函数"""
    return get_config_manager().get_config()


def get_environment_config() -> Dict[str, Any]:
    """获取环境特定配置的便捷函数"""
    return get_config_manager().get_environment_config()


def reload_config() -> bool:
    """重载配置的便捷函数"""
    return get_config_manager().reload_config()


# LLM Configuration
class LLMConfig(BaseModel):
    DEEPSEEK_API_KEY: str = Field(default="sk-7b9efb9c2ed240dfbd97d8421706b2c7", description="DeepSeek API Key")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com", description="DeepSeek Base URL")
    DEEPSEEK_MODEL_NAME: str = Field(default="deepseek-chat", description="DeepSeek Model Name")
    
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    OPENAI_MODEL_NAME: str = Field(default="gpt-4o")
    
    ZHIPU_API_KEY: Optional[str] = Field(default=None)
    ZHIPU_MODEL_URL: str = Field(default="https://open.bigmodel.cn/api/paas/v4/")
    ZHIPU_MODEL_NAME: str = Field(default="glm-4.5v")

    # 账户测试信息
    TEST_ACCOUNT_ID: str = Field(default="94267098699")
    TEST_ACCOUNT_NAME: str = Field(default="花语堂")

# Global LLM settings
llm_settings = LLMConfig()
