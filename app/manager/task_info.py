"""
任务信息数据结构模块

定义任务调度器中使用的任务信息数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.manager.task_manager import TaskManager

from app.data.constants import TaskMode


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"       # 正在执行
    PAUSED = "paused"         # 已暂停
    COMPLETED = "completed"   # 已完成
    ERROR = "error"           # 执行错误


@dataclass
class TaskInfo:
    """任务信息数据结构"""
    task_id: str
    account_id: str
    account_name: str
    task_type: str
    task_manager: 'TaskManager'  # 使用字符串类型避免循环导入
    interval: int  # 执行间隔（秒）
    valid_time_range: Optional[List[int]]  # 有效时间范围 [start_hour, end_hour]，None 表示无限制
    task_end_time: date  # 任务结束时间
    
    # 可选字段（有默认值）
    status: TaskStatus = TaskStatus.PENDING
    mode: TaskMode = TaskMode.STANDARD  # 任务执行模式，默认为标准模式
    interaction_note_count: int = 3  # 互动笔记数量，默认3，最大值5
    last_execution_time: Optional[datetime] = None  # 上次执行时间
    next_execution_time: Optional[datetime] = None  # 下次执行时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    kwargs: dict = field(default_factory=dict)  # 任务创建参数
    login_status: Optional[bool] = None  # 登录状态：True=已登录，False=未登录，None=未知
    login_status_checked_at: Optional[datetime] = None  # 登录状态检查时间
    
    def update_status(self, new_status: TaskStatus):
        """更新任务状态"""
        self.status = new_status
        self.updated_at = datetime.now()
    
    def update_execution_time(self, execution_time: datetime):
        """更新执行时间"""
        self.last_execution_time = execution_time
        self.updated_at = datetime.now()
    
    def update_next_execution_time(self, next_time: Optional[datetime]):
        """更新下次执行时间"""
        self.next_execution_time = next_time
        self.updated_at = datetime.now()
    
    def __repr__(self):
        return (
            f"TaskInfo(task_id={self.task_id}, account_id={self.account_id}, "
            f"status={self.status.value}, next_execution_time={self.next_execution_time})"
        )

