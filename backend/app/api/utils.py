"""
API 工具函数
"""

from datetime import date, datetime
from app.api.models import TaskInfoResponse
from app.manager.task_info import TaskInfo


def task_info_to_response(task_info: TaskInfo) -> TaskInfoResponse:
    """
    将 TaskInfo 转换为响应模型
    
    Args:
        task_info: 任务信息对象
        
    Returns:
        TaskInfoResponse: 响应模型
    """
    return TaskInfoResponse(
        task_id=task_info.task_id,
        account_id=task_info.account_id,
        account_name=task_info.account_name,
        task_type=task_info.task_type,
        status=task_info.status.value,
        interval=task_info.interval,
        valid_time_range=task_info.valid_time_range,
        task_end_time=task_info.task_end_time.isoformat() if isinstance(task_info.task_end_time, date) else str(task_info.task_end_time),
        last_execution_time=task_info.last_execution_time.isoformat() if task_info.last_execution_time else None,
        next_execution_time=task_info.next_execution_time.isoformat() if task_info.next_execution_time else None,
        created_at=task_info.created_at.isoformat() if task_info.created_at else None,
        updated_at=task_info.updated_at.isoformat() if task_info.updated_at else None,
        round_num=getattr(task_info.task_manager, 'round_num', None),
        mode=task_info.mode.value if hasattr(task_info.mode, 'value') else str(task_info.mode),
        interaction_note_count=task_info.interaction_note_count,
        kwargs=task_info.kwargs,
        login_status=task_info.login_status,
        login_status_checked_at=task_info.login_status_checked_at.isoformat() if task_info.login_status_checked_at else None
    )

