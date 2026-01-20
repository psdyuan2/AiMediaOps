"""
账户管理路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.models import TaskListResponse
from app.api.dependencies import get_dispatcher
from app.api.utils import task_info_to_response
from app.manager.task_dispatcher import TaskDispatcher
from app.core.logger import logger

router = APIRouter()


@router.get("/{account_id}/tasks", response_model=TaskListResponse, tags=["账户管理"])
async def get_account_tasks(
    account_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    获取账户的任务列表
    
    根据账户ID获取该账户下的所有任务
    """
    try:
        # 获取账户的任务列表
        tasks = dispatcher.list_tasks(account_id=account_id)
        
        # 转换为响应模型
        task_responses = [task_info_to_response(task) for task in tasks]
        
        return TaskListResponse(
            total=len(task_responses),
            tasks=task_responses
        )
    
    except Exception as e:
        logger.error(f"获取账户任务列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取账户任务列表失败: {str(e)}"
        )

