"""
Configuration Manager Module

This module provides centralized configuration management for the context storage
and agent system. Supports hot-reloading, validation, and environment-specific
settings.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
import logging

# 配置文件路径
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "context_storage_config.yaml"
ENV_CONFIG_PATH = os.getenv("CONTEXT_STORAGE_CONFIG_PATH", "")

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


class CompressionAlgorithm(str, Enum):
    """压缩算法枚举"""
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


class StorageConfig(BaseModel):
    """存储配置"""
    root_directory: str = Field(default="context_storage", description="存储根目录")
    database_type: DatabaseType = Field(default=DatabaseType.SQLITE, description="数据库类型")

    class BackupConfig(BaseModel):
        enabled: bool = Field(default=True, description="是否启用自动备份")
        schedule: str = Field(default="daily", description="备份计划 (hourly, daily, weekly)")
        retention_days: int = Field(default=30, description="备份保留天数")
        compression: bool = Field(default=True, description="是否压缩备份")

    backup: BackupConfig = Field(default_factory=BackupConfig, description="自动备份配置")


class SplittingConfig(BaseModel):
    """内容切分配置"""

    class TriggersConfig(BaseModel):
        max_block_size_tokens: int = Field(default=10000, ge=1000, le=50000,
                                           description="基于Token数量的切分阈值")
        max_time_interval_seconds: int = Field(default=3600, ge=300, le=86400,
                                            description="基于时间的切分阈值(秒)")
        semantic_boundary_detection: bool = Field(default=True, description="是否启用语义边界检测")

        class DelayedStorageConfig(BaseModel):
            enabled: bool = Field(default=True, description="是否启用延迟存储")
            delay_seconds: int = Field(default=300, ge=60, le=3600,
                                   description="延迟存储时间(秒)")
            max_pending_blocks: int = Field(default=10, ge=5, le=50,
                                        description="最大待存储块数量")

        delay_storage: DelayedStorageConfig = Field(default_factory=DelayedStorageConfig,
                                                description="延迟存储配置")

    triggers: TriggersConfig = Field(default_factory=TriggersConfig, description="切分触发配置")

    class StrategiesConfig(BaseModel):
        topic_similarity_threshold: float = Field(default=0.7, ge=0.5, le=1.0,
                                                 description="主题相似度阈值")
        min_paragraph_length: int = Field(default=50, ge=10, le=200,
                                       description="段落最小长度")

        task_boundary_keywords: List[str] = Field(
            default=["总结", "下一步", "另外", "然后", "开始", "结束", "完成"],
            description="任务边界关键词列表"
        )

    strategies: StrategiesConfig = Field(default_factory=StrategiesConfig, description="智能切分策略")


class NamingConfig(BaseModel):
    """文件命名配置"""
    convention: NamingConvention = Field(default=NamingConvention.TIMESTAMP_ENGLISH,
                                      description="文件命名策略")

    class SummaryGenerationConfig(BaseModel):
        max_words: int = Field(default=5, ge=2, le=10, description="摘要最大英文单词数")
        use_llm_generation: bool = Field(default=True, description="是否使用LLM生成名称")

        content_sources: List[str] = Field(
            default=["user_goal", "current_task", "key_topics", "agent_actions"],
            description="摘要内容来源"
        )

    summary_generation: SummaryGenerationConfig = Field(default_factory=SummaryGenerationConfig,
                                                 description="英文摘要生成配置")

    class SanitizationConfig(BaseModel):
        remove_chars: str = Field(default="!@#$%^&*()+=[]{}|\\:;\"'<>?,./",
                                    description="要移除的特殊字符")
        replace_with_underscore: str = Field(default=" -", description="替换为下划线的字符")
        max_length: int = Field(default=50, ge=20, le=100, description="最大文件名长度")

    sanitization: SanitizationConfig = Field(default_factory=SanitizationConfig,
                                        description="文件名清理配置")


class AgentConfig(BaseModel):
    """智能体配置"""
    class InitialContextConfig(BaseModel):
        default_time_window: str = Field(default="24h",
                                      description="默认时间窗口 (1h, 6h, 24h, 7d, 30d)")
        default_search_type: str = Field(default="summary",
                                     description="默认搜索类型 (summary, filename, keywords, full_content)")
        default_max_blocks: int = Field(default=5, ge=1, le=20, description="默认加载的最大上下文块数")
        auto_expand_window: bool = Field(default=True, description="是否自动扩展时间窗口")
        relevance_threshold: int = Field(default=70, ge=50, le=95, description="上下文相关性阈值(0-100)")

    initial_context: InitialContextConfig = Field(default_factory=InitialContextConfig,
                                             description="初始化上下文配置")

    class RetrievalConfig(BaseModel):
        keyword_weight: float = Field(default=0.4, ge=0.1, le=1.0, description="关键词搜索权重")
        time_weight: float = Field(default=0.3, ge=0.1, le=1.0, description="时间相似度权重")
        semantic_weight: float = Field(default=0.3, ge=0.1, le=1.0, description="语义相似度权重")
        max_results: int = Field(default=10, ge=5, le=50, description="最大检索结果数")

    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig, description="智能检索策略")


class DatabaseConfig(BaseModel):
    """数据库配置"""

    class SQLiteConfig(BaseModel):
        path: str = Field(default="database/context_blocks.db", description="数据库文件路径")
        max_connections: int = Field(default=5, ge=1, le=20, description="最大连接数")
        timeout: int = Field(default=30, ge=5, le=300, description="连接超时时间(秒)")
        enable_wal: bool = Field(default=True, description="是否启用WAL模式")
        sync_mode: SyncMode = Field(default=SyncMode.NORMAL, description="同步模式")

    class PostgreSQLConfig(BaseModel):
        host: str = Field(default="localhost", description="PostgreSQL主机")
        port: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL端口")
        database: str = Field(default="context_storage", description="数据库名称")
        username: str = Field(default="postgres", description="用户名")
        password: str = Field(default="", description="密码")
        pool_size: int = Field(default=5, ge=1, le=20, description="连接池大小")
        timeout: int = Field(default=30, ge=5, le=300, description="连接超时时间(秒)")

    sqlite: SQLiteConfig = Field(default_factory=SQLiteConfig, description="SQLite配置")
    postgresql: PostgreSQLConfig = Field(default_factory=PostgreSQLConfig, description="PostgreSQL配置")

    class IndexConfig(BaseModel):
        auto_build: bool = Field(default=True, description="是否自动构建索引")
        rebuild_interval: int = Field(default=24, ge=1, le=168, description="索引重建间隔(小时)")
        full_text_search: bool = Field(default=True, description="是否启用全文搜索")

    indexing: IndexConfig = Field(default_factory=IndexConfig, description="索引配置")


class PerformanceConfig(BaseModel):
    """性能优化配置"""

    class CacheConfig(BaseModel):
        max_memory_mb: int = Field(default=100, ge=10, le=1000, description="内存缓存大小(MB)")
        ttl_seconds: int = Field(default=1800, ge=300, le=7200, description="缓存过期时间(秒)")
        enable_disk_cache: bool = Field(default=True, description="是否启用磁盘缓存")
        max_disk_mb: int = Field(default=500, ge=100, le=5000, description="磁盘缓存大小(MB)")

    cache: CacheConfig = Field(default_factory=CacheConfig, description="缓存配置")

    class ConcurrencyConfig(BaseModel):
        max_concurrent_searches: int = Field(default=3, ge=1, le=10, description="最大并发搜索数")
        search_timeout: int = Field(default=30, ge=5, le=120, description="搜索超时时间(秒)")
        batch_size: int = Field(default=100, ge=10, le=1000, description="批量操作大小")

    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig, description="并发配置")

    class CompressionConfig(BaseModel):
        enabled: bool = Field(default=True, description="是否启用数据压缩")
        algorithm: CompressionAlgorithm = Field(default=CompressionAlgorithm.GZIP,
                                            description="压缩算法")
        min_size_bytes: int = Field(default=1024, ge=512, le=10240, description="压缩阈值(字节)")

    compression: CompressionConfig = Field(default_factory=CompressionConfig, description="压缩配置")


class MonitoringConfig(BaseModel):
    """监控和日志配置"""

    class LoggingConfig(BaseModel):
        level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
        file_path: str = Field(default="logs/context_storage.log", description="日志文件路径")
        max_file_size_mb: int = Field(default=50, ge=1, le=500, description="最大日志文件大小(MB)")
        retain_files: int = Field(default=5, ge=1, le=50, description="保留的日志文件数")
        detailed_operations: bool = Field(default=True, description="是否记录详细操作")

    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")

    class MetricsConfig(BaseModel):
        enabled: bool = Field(default=True, description="是否启用性能指标收集")
        interval_seconds: int = Field(default=60, ge=10, le=3600, description="指标收集间隔(秒)")
        slow_query_threshold_ms: int = Field(default=1000, ge=100, le=10000, description="慢查询阈值(毫秒)")

    metrics: MetricsConfig = Field(default_factory=MetricsConfig, description="性能指标配置")


class SecurityConfig(BaseModel):
    """安全配置"""

    class EncryptionConfig(BaseModel):
        enabled: bool = Field(default=False, description="是否启用静态数据加密")
        algorithm: str = Field(default="AES-256-GCM", description="加密算法")
        key_source: str = Field(default="env", description="密钥来源")

    encryption: EncryptionConfig = Field(default_factory=EncryptionConfig, description="加密配置")

    class AccessConfig(BaseModel):
        enabled: bool = Field(default=False, description="是否启用访问控制")
        max_file_permissions: str = Field(default="644", description="最大文件访问权限")

    access_control: AccessConfig = Field(default_factory=AccessConfig, description="访问控制配置")


class ContextStorageConfig(BaseModel):
    """完整的上下文存储配置"""

    storage: StorageConfig = Field(default_factory=StorageConfig, description="存储配置")
    splitting: SplittingConfig = Field(default_factory=SplittingConfig, description="内容切分配置")
    naming: NamingConfig = Field(default_factory=NamingConfig, description="文件命名配置")
    agent: AgentConfig = Field(default_factory=AgentConfig, description="智能体配置")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="数据库配置")
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig, description="性能配置")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="监控配置")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="安全配置")

    # 环境特定配置
    development: Optional[Dict[str, Any]] = Field(default=None, description="开发环境配置")
    testing: Optional[Dict[str, Any]] = Field(default=None, description="测试环境配置")
    production: Optional[Dict[str, Any]] = Field(default=None, description="生产环境配置")

    # 元数据
    config_version: str = Field(default="1.0.0", description="配置版本")
    last_modified: Optional[str] = Field(default=None, description="最后修改时间")
    compatible_agent_version: str = Field(default="1.0.0", description="兼容的智能体版本")
    schema_version: str = Field(default="1.0", description="配置模式版本")


class ConfigManager:
    """配置管理器 - 支持热重载和环境特定配置"""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为项目config目录
        """
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._config: Optional[ContextStorageConfig] = None
        self._last_modified = 0

        # 加载配置
        self.reload_config()

        # 设置日志
        self._setup_logging()

        logger.info(f"✅ ConfigManager initialized with config: {self.config_path}")
        logger.info(f"📊 Current environment: {self.get_environment()}")

    def _setup_logging(self):
        """设置日志系统"""
        config = self.get_config()

        # 创建日志目录
        log_path = Path(config.storage.root_directory) / config.monitoring.logging.file_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 配置日志格式
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # 设置日志级别
        level = getattr(logging, config.monitoring.logging.level.value)

        # 配置文件处理器
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=config.monitoring.logging.max_file_size_mb * 1024 * 1024,
            backupCount=config.monitoring.logging.retain_files,
            encoding='utf-8'
        )

        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format))

        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.addHandler(file_handler)

        # 如果启用详细操作日志
        if config.monitoring.logging.detailed_operations:
            # 可以添加更详细的操作日志处理器
            pass

    def get_environment(self) -> str:
        """获取当前环境"""
        env = os.getenv("CONTEXT_ENV", "development")
        return env.lower()

    def get_config(self) -> ContextStorageConfig:
        """获取当前环境的完整配置"""
        if self._config is None:
            self.reload_config()

        return self._config

    def get_environment_config(self) -> Dict[str, Any]:
        """获取环境特定的配置覆盖"""
        environment = self.get_environment()
        config = self.get_config()

        # 基础配置
        base_config = config.dict()

        # 应用环境特定覆盖
        env_config = getattr(config, environment, None)
        if env_config:
            base_config.update(env_config)
            logger.debug(f"🔧 Applied {environment} environment overrides")

        return base_config

    def reload_config(self) -> bool:
        """重载配置文件"""
        try:
            if not self.config_path.exists():
                logger.warning(f"⚠️ Config file not found: {self.config_path}, using defaults")
                self._config = ContextStorageConfig()
                return True

            # 检查文件修改时间
            current_modified = self.config_path.stat().st_mtime
            if current_modified <= self._last_modified:
                return True  # 无需重载

            # 加载YAML配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            # 验证并创建配置对象
            self._config = ContextStorageConfig(**config_data)
            self._last_modified = current_modified

            logger.info(f"🔄 Configuration reloaded successfully")
            logger.debug(f"📋 Config loaded with {len(config_data)} sections")

            return True

        except yaml.YAMLError as e:
            logger.error(f"❌ YAML parsing error in {self.config_path}: {e}")
            if self._config is None:
                self._config = ContextStorageConfig()  # 使用默认配置
            return False
        except Exception as e:
            logger.error(f"❌ Error loading config from {self.config_path}: {e}")
            if self._config is None:
                self._config = ContextStorageConfig()  # 使用默认配置
            return False

    def get_storage_path(self) -> Path:
        """获取存储根目录路径"""
        config = self.get_config()
        base_path = config.storage.root_directory

        # 环境特定路径覆盖
        environment = self.get_environment()
        env_overrides = getattr(config, environment, {})
        if 'storage' in env_overrides and 'root_directory' in env_overrides['storage']:
            base_path = env_overrides['storage']['root_directory']

        # 创建绝对路径
        if not Path(base_path).is_absolute():
            base_path = Path(__file__).parent.parent.parent / base_path

        return Path(base_path)

    def validate_config(self) -> List[str]:
        """验证配置有效性"""
        config = self.get_config()
        errors = []

        # 验证存储路径
        try:
            storage_path = self.get_storage_path()
            storage_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Storage directory error: {e}")

        # 验证时间窗口格式
        valid_time_windows = ["1h", "6h", "24h", "7d", "30d"]
        if config.agent.initial_context.default_time_window not in valid_time_windows:
            errors.append(f"Invalid time window: {config.agent.initial_context.default_time_window}")

        # 验证阈值范围
        if not (50 <= config.agent.retrieval.relevance_threshold <= 95):
            errors.append("Relevance threshold must be between 50 and 95")

        # 验证权重和为1.0
        total_weight = (config.agent.retrieval.keyword_weight +
                      config.agent.retrieval.time_weight +
                      config.agent.retrieval.semantic_weight)
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"Retrieval weights must sum to 1.0, current sum: {total_weight}")

        if errors:
            logger.warning(f"⚠️ Configuration validation errors: {errors}")
        else:
            logger.info("✅ Configuration validation passed")

        return errors

    def save_config(self, config_path: Optional[Path] = None) -> bool:
        """保存当前配置到文件"""
        try:
            target_path = config_path if config_path else self.config_path
            target_path.parent.mkdir(parents=True, exist_ok=True)

            config_data = self.get_config().dict()
            config_data['last_modified'] = self._get_current_timestamp()

            with open(target_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False,
                         allow_unicode=True, indent=2)

            logger.info(f"💾 Configuration saved to {target_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving configuration: {e}")
            return False

    def update_config(self, **kwargs) -> bool:
        """动态更新配置项"""
        try:
            config_dict = self.get_config().dict()

            # 递归更新配置
            self._deep_update(config_dict, kwargs)

            # 验证新配置
            new_config = ContextStorageConfig(**config_dict)
            validation_errors = self.validate_config()

            if validation_errors:
                logger.error(f"❌ Configuration update validation failed: {validation_errors}")
                return False

            # 更新配置
            self._config = new_config
            logger.info(f"🔄 Configuration updated with: {list(kwargs.keys())}")
            return True

        except Exception as e:
            logger.error(f"❌ Error updating configuration: {e}")
            return False

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