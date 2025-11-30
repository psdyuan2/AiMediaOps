"""
配置工具函数
简单的KEY=VALUE格式配置管理工具
"""

import os
from typing import Any, Dict, Optional, Union


def get_config_value(key: str, default: Any = None, value_type: type = str) -> Any:
    """
    获取配置值

    Args:
        key: 配置键名
        default: 默认值
        value_type: 期望的值类型

    Returns:
        配置值（转换为指定类型）
    """
    value = os.getenv(key, default)
    if value is None:
        return default

    try:
        if value_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif value_type == int:
            return int(value)
        elif value_type == float:
            return float(value)
        elif value_type == list:
            return [item.strip() for item in value.split(',')]
        else:
            return value_type(value)
    except (ValueError, TypeError):
        return default


def get_context_config() -> Dict[str, Any]:
    """获取上下文存储相关配置"""
    return {
        # 存储配置
        'storage_root': get_config_value('CONTEXT_STORAGE_ROOT', 'context_storage'),
        'max_block_size': get_config_value('CONTEXT_STORAGE_MAX_BLOCK_SIZE', 10000, int),
        'max_time_interval': get_config_value('CONTEXT_STORAGE_MAX_TIME_INTERVAL', 3600, int),
        'db_type': get_config_value('CONTEXT_STORAGE_DB_TYPE', 'sqlite'),
        'db_path': get_config_value('CONTEXT_STORAGE_DB_PATH', 'database/context_blocks.db'),
        'backup_enabled': get_config_value('CONTEXT_STORAGE_BACKUP_ENABLED', True, bool),
        'backup_schedule': get_config_value('CONTEXT_STORAGE_BACKUP_SCHEDULE', 'daily'),
        'backup_retention_days': get_config_value('CONTEXT_STORAGE_BACKUP_RETENTION_DAYS', 30, int),

        # 文件命名配置
        'naming_convention': get_config_value('CONTEXT_STORAGE_NAMING_CONVENTION', 'timestamp_english_summary'),
        'max_words': get_config_value('CONTEXT_STORAGE_MAX_WORDS', 5, int),
        'use_llm_generation': get_config_value('CONTEXT_STORAGE_USE_LLM_GENERATION', True, bool),
        'max_length': get_config_value('CONTEXT_STORAGE_MAX_LENGTH', 50, int),

        # 智能体配置
        'default_time_window': get_config_value('CONTEXT_STORAGE_DEFAULT_TIME_WINDOW', '24h'),
        'default_search_type': get_config_value('CONTEXT_STORAGE_DEFAULT_SEARCH_TYPE', 'summary'),
        'default_max_blocks': get_config_value('CONTEXT_STORAGE_DEFAULT_MAX_BLOCKS', 5, int),
        'auto_expand_window': get_config_value('CONTEXT_STORAGE_AUTO_EXPAND_WINDOW', True, bool),
        'relevance_threshold': get_config_value('CONTEXT_STORAGE_RELEVANCE_THRESHOLD', 70, int),

        # 检索配置
        'keyword_weight': get_config_value('CONTEXT_STORAGE_KEYWORD_WEIGHT', 0.4, float),
        'time_weight': get_config_value('CONTEXT_STORAGE_TIME_WEIGHT', 0.3, float),
        'semantic_weight': get_config_value('CONTEXT_STORAGE_SEMANTIC_WEIGHT', 0.3, float),
        'max_results': get_config_value('CONTEXT_STORAGE_MAX_RESULTS', 10, int),

        # 缓存配置
        'cache_enabled': get_config_value('CONTEXT_STORAGE_CACHE_ENABLED', True, bool),
        'max_memory_mb': get_config_value('CONTEXT_STORAGE_MAX_MEMORY_MB', 100, int),
        'cache_ttl_seconds': get_config_value('CONTEXT_STORAGE_CACHE_TTL_SECONDS', 1800, int),
        'enable_disk_cache': get_config_value('CONTEXT_STORAGE_ENABLE_DISK_CACHE', True, bool),
        'max_disk_mb': get_config_value('CONTEXT_STORAGE_MAX_DISK_MB', 500, int),

        # 并发配置
        'max_concurrent_searches': get_config_value('CONTEXT_STORAGE_MAX_CONCURRENT_SEARCHES', 3, int),
        'search_timeout': get_config_value('CONTEXT_STORAGE_SEARCH_TIMEOUT', 30, int),
        'batch_size': get_config_value('CONTEXT_STORAGE_BATCH_SIZE', 100, int),

        # 日志配置
        'log_level': get_config_value('CONTEXT_STORAGE_LOG_LEVEL', 'INFO'),
        'log_path': get_config_value('CONTEXT_STORAGE_LOG_PATH', 'logs/context_storage.log'),
        'max_file_size_mb': get_config_value('CONTEXT_STORAGE_MAX_FILE_SIZE_MB', 50, int),
        'retain_files': get_config_value('CONTEXT_STORAGE_RETAIN_FILES', 5, int),
        'detailed_operations': get_config_value('CONTEXT_STORAGE_DETAILED_OPERATIONS', True, bool),

        # 性能监控
        'metrics_enabled': get_config_value('CONTEXT_STORAGE_METRICS_ENABLED', True, bool),
        'metrics_interval_seconds': get_config_value('CONTEXT_STORAGE_METRICS_INTERVAL_SECONDS', 60, int),
        'slow_query_threshold_ms': get_config_value('CONTEXT_STORAGE_SLOW_QUERY_THRESHOLD_MS', 1000, int),

        # 安全配置
        'encryption_enabled': get_config_value('CONTEXT_STORAGE_ENCRYPTION_ENABLED', False, bool),
        'access_control_enabled': get_config_value('CONTEXT_STORAGE_ACCESS_CONTROL_ENABLED', False, bool),
    }


def set_config_value(key: str, value: Any) -> bool:
    """
    设置配置值（仅限当前进程）

    Args:
        key: 配置键名
        value: 配置值

    Returns:
        是否设置成功
    """
    os.environ[key] = str(value)
    return True


def update_config_file(key: str, value: Any, env_file_path: str = '.env') -> bool:
    """
    更新.env文件中的配置

    Args:
        key: 配置键名
        value: 配置值
        env_file_path: .env文件路径

    Returns:
        是否更新成功
    """
    try:
        # 读取现有配置
        config_lines = []
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r', encoding='utf-8') as f:
                config_lines = f.readlines()

        # 查找并更新配置行
        key_found = False
        for i, line in enumerate(config_lines):
            if line.startswith(f'{key}='):
                config_lines[i] = f'{key}={value}'
                key_found = True
                break

        # 如果键不存在，添加新行
        if not key_found:
            config_lines.append(f'{key}={value}\n')

        # 写回文件
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.writelines(config_lines)

        return True

    except Exception as e:
        print(f"Error updating config file {env_file_path}: {e}")
        return False


def get_all_config() -> Dict[str, Any]:
    """获取所有配置"""
    return {
        'all': {k: v for k, v in os.environ.items() if k.startswith('CONTEXT_STORAGE_')},
    }


def print_current_config():
    """打印当前配置"""
    config = get_context_config()

    print("🔧 当前上下文存储配置:")
    print("=" * 50)

    sections = {
        '存储配置': ['storage_root', 'max_block_size', 'max_time_interval', 'db_type', 'db_path', 'backup_enabled', 'backup_schedule'],
        '文件命名配置': ['naming_convention', 'max_words', 'use_llm_generation', 'max_length'],
        '智能体配置': ['default_time_window', 'default_search_type', 'default_max_blocks', 'auto_expand_window', 'relevance_threshold'],
        '检索配置': ['keyword_weight', 'time_weight', 'semantic_weight', 'max_results'],
        '缓存配置': ['cache_enabled', 'max_memory_mb', 'cache_ttl_seconds', 'enable_disk_cache', 'max_disk_mb'],
        '并发配置': ['max_concurrent_searches', 'search_timeout', 'batch_size'],
        '日志配置': ['log_level', 'log_path', 'max_file_size_mb', 'retain_files', 'detailed_operations'],
        '性能监控': ['metrics_enabled', 'metrics_interval_seconds', 'slow_query_threshold_ms'],
        '安全配置': ['encryption_enabled', 'access_control_enabled']
    }

    for section_name, keys in sections.items():
        print(f"\n{section_name}:")
        for key in keys:
            value = config.get(key, 'N/A')
            print(f"  {key}: {value}")

    print("\n" + "=" * 50)


def validate_config() -> Dict[str, str]:
    """验证配置有效性"""
    config = get_context_config()
    errors = []

    # 验证存储配置
    if not isinstance(config['max_block_size'], int) or config['max_block_size'] < 1000:
        errors.append("max_block_size must be at least 1000")

    if not isinstance(config['relevance_threshold'], int) or not (50 <= config['relevance_threshold'] <= 95):
        errors.append("relevance_threshold must be between 50 and 95")

    # 验证命名配置
    if config['max_words'] < 2 or config['max_words'] > 20:
        errors.append("max_words must be between 2 and 20")

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }