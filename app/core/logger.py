"""
统一日志管理模块 - 基于loguru的日志系统

本模块提供统一的日志配置和管理，支持：
1. 动态配置日志级别和格式
2. 控制台和文件日志输出
3. 环境变量配置覆盖
4. 全局logger实例

使用示例：
    from app.core.logger import logger, configure_logger

    # 配置日志（可选，默认已使用app.data.config中的配置）
    configure_logger()

    # 使用logger
    logger.info("信息日志")
    logger.error("错误日志")

设计原则：
- 奥卡姆剃刀原则：保持简洁，避免过度设计
- 配置集中化：所有日志配置通过app.data.config中的常量管理
- 向后兼容：导出loguru的logger对象，保持原有API
"""

import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

from loguru import logger as loguru_logger

from app.data.config import (
    LOG_LEVEL,
    LOG_ENABLE_COLOR,
    LOG_SHOW_TIMESTAMP,
    LOG_SHOW_MODULE,
    LOG_SHOW_FUNCTION,
    LOG_TO_FILE,
    LOG_FILE_PATH,
)


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """从字符串转换为日志级别枚举"""
        level_str = level_str.upper()
        for level in cls:
            if level.value == level_str:
                return level
        # 默认返回INFO级别
        return cls.INFO


class LoggerConfig:
    """
    日志配置管理器

    提供统一的日志配置接口，支持：
    - 动态调整日志级别
    - 控制日志输出格式
    - 环境变量配置覆盖
    """

    def __init__(self):
        # 默认配置使用config.py中的常量
        self._level = LogLevel.from_string(LOG_LEVEL)
        self._enable_color = LOG_ENABLE_COLOR
        self._show_timestamp = LOG_SHOW_TIMESTAMP
        self._show_module = LOG_SHOW_MODULE
        self._show_function = LOG_SHOW_FUNCTION
        self._log_to_file = LOG_TO_FILE
        self._log_file_path = LOG_FILE_PATH

        # 注意：这里不再从环境变量加载，因为config.py已经处理了环境变量

    @property
    def level(self) -> LogLevel:
        """获取当前日志级别"""
        return self._level

    @level.setter
    def level(self, level: LogLevel):
        """设置日志级别"""
        self._level = level

    def set_level(self, level: str):
        """通过字符串设置日志级别"""
        self._level = LogLevel.from_string(level)

    @property
    def enable_color(self) -> bool:
        """是否启用颜色"""
        return self._enable_color

    @property
    def show_timestamp(self) -> bool:
        """是否显示时间戳"""
        return self._show_timestamp

    @property
    def show_module(self) -> bool:
        """是否显示模块名"""
        return self._show_module

    @property
    def show_function(self) -> bool:
        """是否显示函数名"""
        return self._show_function

    @property
    def log_to_file(self) -> bool:
        """是否输出到文件"""
        return self._log_to_file

    @property
    def log_file_path(self) -> str:
        """日志文件路径"""
        return self._log_file_path

    def get_format_string(self) -> str:
        """
        获取日志格式字符串

        Returns:
            格式化的日志格式字符串
        """
        format_parts = []

        if self._show_timestamp:
            format_parts.append("<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>")

        if self._show_module:
            format_parts.append("<cyan>{name}</cyan>")

        if self._show_function:
            format_parts.append("<magenta>{function}</magenta>")

        format_parts.append("<level>{level}</level>")
        format_parts.append("<level>{message}</level>")

        return " | ".join(format_parts)

    def to_dict(self) -> dict:
        """将配置转换为字典"""
        return {
            "level": self._level.value,
            "enable_color": self._enable_color,
            "show_timestamp": self._show_timestamp,
            "show_module": self._show_module,
            "show_function": self._show_function,
            "log_to_file": self._log_to_file,
            "log_file_path": self._log_file_path,
        }

    def __str__(self) -> str:
        """字符串表示"""
        config_dict = self.to_dict()
        return f"LoggerConfig({config_dict})"


# 全局日志配置实例
logger_config = LoggerConfig()


def setup_logger_config(
    level: Optional[str] = None,
    enable_color: Optional[bool] = None,
    show_timestamp: Optional[bool] = None,
    show_module: Optional[bool] = None,
    show_function: Optional[bool] = None,
    log_to_file: Optional[bool] = None,
    log_file_path: Optional[str] = None,
):
    """
    快速设置日志配置

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_color: 是否启用颜色
        show_timestamp: 是否显示时间戳
        show_module: 是否显示模块名
        show_function: 是否显示函数名
        log_to_file: 是否输出到文件
        log_file_path: 日志文件路径
    """
    global logger_config

    if level is not None:
        logger_config.set_level(level)

    if enable_color is not None:
        logger_config._enable_color = enable_color

    if show_timestamp is not None:
        logger_config._show_timestamp = show_timestamp

    if show_module is not None:
        logger_config._show_module = show_module

    if show_function is not None:
        logger_config._show_function = show_function

    if log_to_file is not None:
        logger_config._log_to_file = log_to_file

    if log_file_path is not None:
        logger_config._log_file_path = log_file_path


def configure_logger(
    level: Optional[str] = None,
    enable_color: Optional[bool] = None,
    show_timestamp: Optional[bool] = None,
    show_module: Optional[bool] = None,
    show_function: Optional[bool] = None,
    log_to_file: Optional[bool] = None,
    log_file_path: Optional[str] = None,
):
    """
    配置loguru日志格式和级别

    可以通过参数临时覆盖配置，不传参数则使用logger_config的配置

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_color: 是否启用颜色
        show_timestamp: 是否显示时间戳
        show_module: 是否显示模块名
        show_function: 是否显示函数名
        log_to_file: 是否输出到文件
        log_file_path: 日志文件路径
    """
    # 如果提供了参数，临时更新配置
    if any([level, enable_color is not None, show_timestamp is not None,
            show_module is not None, show_function is not None,
            log_to_file is not None, log_file_path]):
        setup_logger_config(
            level=level,
            enable_color=enable_color,
            show_timestamp=show_timestamp,
            show_module=show_module,
            show_function=show_function,
            log_to_file=log_to_file,
            log_file_path=log_file_path
        )

    # 移除loguru默认处理器
    loguru_logger.remove()

    # 根据配置添加控制台处理器
    log_format = logger_config.get_format_string() if logger_config.enable_color else "{message}"

    loguru_logger.add(
        sink=sys.stderr,
        format=log_format,
        level=logger_config.level.value,
        colorize=logger_config.enable_color
    )

    # 如果需要输出到文件
    if logger_config.log_to_file:
        # 确保日志目录存在
        log_dir = Path(logger_config.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        loguru_logger.add(
            sink=logger_config.log_file_path,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name} | {function} | {message}",
            level=logger_config.level.value,
            rotation="10 MB",
            retention="30 days",
            encoding="utf-8"
        )

    loguru_logger.debug(f"日志配置已应用: {logger_config.to_dict()}")


def get_logger(name: Optional[str] = None):
    """
    获取logger实例

    Args:
        name: logger名称，用于区分不同模块的日志

    Returns:
        loguru的logger对象
    """
    if name:
        return loguru_logger.bind(name=name)
    return loguru_logger


# 默认配置logger（使用logger_config的默认配置）
# 注意：这里默认配置一次，但用户可以通过configure_logger()重新配置
configure_logger()

# 导出loguru的logger对象，保持向后兼容
logger = loguru_logger

__all__ = [
    # 核心logger对象
    "logger",
    "configure_logger",
    "get_logger",
    # 配置相关类
    "LogLevel",
    "LoggerConfig",
    "logger_config",
    "setup_logger_config",
]