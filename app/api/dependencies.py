"""
API 依赖注入模块

提供全局的 TaskDispatcher 实例管理
"""

from typing import Optional
from app.manager.task_dispatcher import TaskDispatcher
from app.core.logger import logger

# 全局调度器实例
_dispatcher_instance: Optional[TaskDispatcher] = None


def get_dispatcher() -> TaskDispatcher:
    """
    获取全局 TaskDispatcher 实例（单例模式）
    
    Returns:
        TaskDispatcher: 调度器实例
    """
    global _dispatcher_instance
    if _dispatcher_instance is None:
        logger.info("初始化 TaskDispatcher 实例")
        _dispatcher_instance = TaskDispatcher()
    return _dispatcher_instance


def reset_dispatcher():
    """
    重置调度器实例（主要用于测试）
    """
    global _dispatcher_instance
    _dispatcher_instance = None

