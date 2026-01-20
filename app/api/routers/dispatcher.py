"""
调度器管理路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.models import APIResponse, DispatcherStatusResponse
from app.api.dependencies import get_dispatcher
from app.manager.task_dispatcher import TaskDispatcher
from app.manager.task_info import TaskStatus
from app.core.logger import logger
from app.core.license_manager import get_license_manager, LicenseManager

router = APIRouter()


@router.get("/status", response_model=DispatcherStatusResponse, tags=["调度器管理"])
async def get_dispatcher_status(
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    获取调度器状态
    
    返回调度器的运行状态和任务统计信息
    """
    all_tasks = dispatcher.all_tasks
    
    # 统计各状态任务数量
    status_count = {
        TaskStatus.PENDING: 0,
        TaskStatus.RUNNING: 0,
        TaskStatus.PAUSED: 0,
        TaskStatus.COMPLETED: 0,
        TaskStatus.ERROR: 0
    }
    
    for task_info in all_tasks.values():
        status_count[task_info.status] = status_count.get(task_info.status, 0) + 1
    
    # 获取当前运行的任务信息
    current_running_task = None
    if dispatcher.running_task:
        current_running_task = {
            "task_id": dispatcher.running_task.task_id,
            "account_id": dispatcher.running_task.account_id,
            "started_at": dispatcher.running_task.last_execution_time.isoformat() if dispatcher.running_task.last_execution_time else None
        }
    
    return DispatcherStatusResponse(
        is_running=dispatcher.scheduler_task is not None and not dispatcher.scheduler_task.done(),
        total_tasks=len(all_tasks),
        pending_tasks=status_count[TaskStatus.PENDING],
        running_tasks=status_count[TaskStatus.RUNNING],
        paused_tasks=status_count[TaskStatus.PAUSED],
        completed_tasks=status_count[TaskStatus.COMPLETED],
        error_tasks=status_count[TaskStatus.ERROR],
        current_running_task=current_running_task
    )


@router.post("/start", response_model=APIResponse, tags=["调度器管理"])
async def start_dispatcher(
    dispatcher: TaskDispatcher = Depends(get_dispatcher),
    license_manager: LicenseManager = Depends(get_license_manager),
):
    """
    启动调度器
    
    开始执行任务调度循环
    """
    if dispatcher.scheduler_task is not None and not dispatcher.scheduler_task.done():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="调度器已在运行"
        )
    
    try:
        # 注册码限制：当处于免费模式（未激活或已过期）且任务数量超过免费上限时，禁止启动调度器
        all_tasks = dispatcher.all_tasks
        total_tasks = len(all_tasks)
        max_tasks = license_manager.get_max_tasks()

        # 免费模式（未激活或已过期）
        in_free_mode = (not license_manager.is_activated()) or license_manager.is_expired()
        if in_free_mode and total_tasks > max_tasks:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"当前为免费版或已过期状态，最多允许 {max_tasks} 个任务。"
                    f"当前任务数为 {total_tasks}，超过免费版上限，无法启动调度器。"
                    f"请删除多余任务或重新激活产品后再试。"
                ),
            )

        # 如果在免费模式下，确保所有任务的执行间隔不低于免费版限制
        interval_limit = license_manager.get_interval_limit()
        if in_free_mode and interval_limit is not None:
            adjusted_count = 0
            for task in all_tasks.values():
                if task.interval < interval_limit:
                    task.interval = interval_limit
                    adjusted_count += 1
            if adjusted_count > 0:
                logger.info(
                    f"免费版/过期模式下，已将 {adjusted_count} 个任务的执行间隔调整为 {interval_limit} 秒"
                )

        await dispatcher.start()
        return APIResponse(
            success=True,
            message="调度器已启动"
        )
    except Exception as e:
        logger.error(f"启动调度器失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动调度器失败: {str(e)}"
        )


@router.post("/stop", response_model=APIResponse, tags=["调度器管理"])
async def stop_dispatcher(
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    停止调度器
    
    停止任务调度循环，等待当前任务完成
    """
    if dispatcher.scheduler_task is None or dispatcher.scheduler_task.done():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="调度器未运行"
        )
    
    try:
        await dispatcher.stop()
        return APIResponse(
            success=True,
            message="调度器已停止"
        )
    except Exception as e:
        logger.error(f"停止调度器失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止调度器失败: {str(e)}"
        )

