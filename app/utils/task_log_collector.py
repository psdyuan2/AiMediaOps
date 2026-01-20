"""
任务日志收集器模块

负责收集和存储每个任务的执行日志，支持实时查询和获取。
使用文件存储，按 bindtype 分类，每个日志文件只保留最近 1000 行。
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from app.core.logger import logger as base_logger
from app.data.constants import LogBindType, TASK_DATA_BASE_PATH


@dataclass
class LogEntry:
    """日志条目数据类"""
    timestamp: str
    level: str
    module: str
    function: str
    message: str
    task_id: Optional[str] = None
    bindtype: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


class TaskLogCollector:
    """
    任务日志收集器
    
    收集每个任务的执行日志，存储在文件中，支持按任务ID和 bindtype 查询。
    每个日志文件只保留最近 1000 行。
    """
    
    def __init__(self, log_base_dir: str = None, max_logs_per_file: int = 1000):
        """
        初始化日志收集器
        
        Args:
            log_base_dir: 日志文件基础目录，默认为 app/data/logs/
            max_logs_per_file: 每个日志文件最多保留的日志条数（默认1000）
        """
        if log_base_dir is None:
            # 默认日志目录：app/data/logs/
            # TASK_DATA_BASE_PATH = './app/data/task_data/'
            # 所以日志目录应该是：./app/data/logs/
            log_base_dir = os.path.join(os.path.dirname(TASK_DATA_BASE_PATH.rstrip('/')), 'logs')
        
        self.log_base_dir = Path(log_base_dir)
        self.max_logs_per_file = max_logs_per_file
        
        # 确保日志目录存在
        self.log_base_dir.mkdir(parents=True, exist_ok=True)
        
        # 按 bindtype 创建子目录
        for bindtype in LogBindType:
            (self.log_base_dir / bindtype.value).mkdir(parents=True, exist_ok=True)
        
        # 使用锁保护并发访问
        self._lock = asyncio.Lock()
    
    def _get_log_file_path(self, task_id: str, bindtype: LogBindType) -> Path:
        """
        获取日志文件路径
        
        Args:
            task_id: 任务ID
            bindtype: 日志绑定类型
            
        Returns:
            日志文件路径
        """
        return self.log_base_dir / bindtype.value / f"{task_id}.jsonl"
    
    def _read_log_file(self, file_path: Path) -> List[LogEntry]:
        """
        读取日志文件
        
        Args:
            file_path: 日志文件路径
            
        Returns:
            日志条目列表
        """
        if not file_path.exists():
            return []
        
        log_entries = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        log_dict = json.loads(line)
                        log_entries.append(LogEntry(**log_dict))
                    except (json.JSONDecodeError, TypeError, ValueError) as e:
                        base_logger.debug(f"解析日志行失败: {line[:100]}, error: {e}")
                        continue
        except Exception as e:
            base_logger.error(f"读取日志文件失败: {file_path}, error: {e}")
        
        return log_entries
    
    def _write_log_file(self, file_path: Path, log_entries: List[LogEntry]):
        """
        写入日志文件（只保留最近 max_logs_per_file 行）
        
        Args:
            file_path: 日志文件路径
            log_entries: 日志条目列表
        """
        try:
            # 只保留最近 max_logs_per_file 条
            if len(log_entries) > self.max_logs_per_file:
                log_entries = log_entries[-self.max_logs_per_file:]
            
            # 写入文件（覆盖写入）
            with open(file_path, 'w', encoding='utf-8') as f:
                for entry in log_entries:
                    json_line = json.dumps(entry.to_dict(), ensure_ascii=False)
                    f.write(json_line + '\n')
        except Exception as e:
            base_logger.error(f"写入日志文件失败: {file_path}, error: {e}")
    
    def add_log(
        self,
        task_id: str,
        bindtype: LogBindType,
        level: str,
        message: str,
        module: Optional[str] = None,
        function: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        添加日志条目
        
        Args:
            task_id: 任务ID
            bindtype: 日志绑定类型
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: 日志消息
            module: 模块名（可选）
            function: 函数名（可选）
            timestamp: 时间戳（可选，默认使用当前时间）
        """
        if not task_id or not bindtype:
            return
        
        if timestamp is None:
            timestamp = datetime.now()
        
        log_entry = LogEntry(
            timestamp=timestamp.isoformat(),
            level=level.upper(),
            module=module or "",
            function=function or "",
            message=str(message),
            task_id=task_id,
            bindtype=bindtype.value
        )
        
        # 获取日志文件路径
        log_file = self._get_log_file_path(task_id, bindtype)
        
        # 读取现有日志
        log_entries = self._read_log_file(log_file)
        
        # 添加新日志
        log_entries.append(log_entry)
        
        # 写入文件（只保留最近 max_logs_per_file 条）
        self._write_log_file(log_file, log_entries)
    
    async def add_log_async(
        self,
        task_id: str,
        bindtype: LogBindType,
        level: str,
        message: str,
        module: Optional[str] = None,
        function: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """异步添加日志条目（线程安全）"""
        async with self._lock:
            self.add_log(task_id, bindtype, level, message, module, function, timestamp)
    
    def get_logs(
        self,
        task_id: str,
        bindtype: LogBindType = LogBindType.TASK_LOG,
        since: Optional[datetime] = None,
        level_filter: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[dict]:
        """
        获取任务的日志
        
        Args:
            task_id: 任务ID
            bindtype: 日志绑定类型，默认为 TASK_LOG
            since: 只返回此时间之后的日志（可选）
            level_filter: 日志级别过滤（可选，如 ["INFO", "ERROR"]）
            limit: 最多返回的日志条数（可选）
            
        Returns:
            日志条目列表（字典格式）
        """
        log_file = self._get_log_file_path(task_id, bindtype)
        log_entries = self._read_log_file(log_file)
        
        result = []
        
        # 遍历日志条目（从旧到新）
        for log_entry in log_entries:
            # 时间过滤
            if since:
                try:
                    log_timestamp = datetime.fromisoformat(log_entry.timestamp)
                    if log_timestamp < since:
                        continue
                except (ValueError, TypeError):
                    pass
            
            # 级别过滤
            if level_filter and log_entry.level not in level_filter:
                continue
            
            result.append(log_entry.to_dict())
        
        # 限制数量（如果需要，取最新的 limit 条）
        if limit and limit > 0:
            result = result[-limit:]
        
        return result
    
    async def get_logs_async(
        self,
        task_id: str,
        bindtype: LogBindType = LogBindType.TASK_LOG,
        since: Optional[datetime] = None,
        level_filter: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[dict]:
        """异步获取日志（线程安全）"""
        async with self._lock:
            return self.get_logs(task_id, bindtype, since, level_filter, limit)
    
    def clear_logs(self, task_id: str, bindtype: Optional[LogBindType] = None):
        """
        清空指定任务的日志
        
        Args:
            task_id: 任务ID
            bindtype: 日志绑定类型，如果为 None 则清空所有类型的日志
        """
        if bindtype:
            log_file = self._get_log_file_path(task_id, bindtype)
            if log_file.exists():
                log_file.unlink()
        else:
            # 清空所有类型的日志
            for bindtype_enum in LogBindType:
                log_file = self._get_log_file_path(task_id, bindtype_enum)
                if log_file.exists():
                    log_file.unlink()
    
    async def clear_logs_async(self, task_id: str, bindtype: Optional[LogBindType] = None):
        """异步清空日志（线程安全）"""
        async with self._lock:
            self.clear_logs(task_id, bindtype)
    
    def get_log_count(self, task_id: str, bindtype: LogBindType = LogBindType.TASK_LOG) -> int:
        """获取指定任务的日志条数"""
        log_file = self._get_log_file_path(task_id, bindtype)
        log_entries = self._read_log_file(log_file)
        return len(log_entries)
    
    def remove_task_logs(self, task_id: str):
        """移除指定任务的所有日志（任务删除时调用）"""
        self.clear_logs(task_id, bindtype=None)


# 全局日志收集器实例
_task_log_collector: Optional[TaskLogCollector] = None


def get_task_log_collector() -> TaskLogCollector:
    """获取全局日志收集器实例（单例模式）"""
    global _task_log_collector
    if _task_log_collector is None:
        _task_log_collector = TaskLogCollector(max_logs_per_file=1000)
    return _task_log_collector


def set_task_log_collector(collector: TaskLogCollector):
    """设置全局日志收集器实例"""
    global _task_log_collector
    _task_log_collector = collector
