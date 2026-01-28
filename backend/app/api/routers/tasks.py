"""
任务管理路由
"""

from typing import Optional, List
from datetime import date as date_type
import asyncio
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from app.api.models import (
    TaskCreateRequest, TaskCreateResponse, TaskInfoResponse,
    TaskListResponse, TaskReorderRequest, TaskExecuteRequest, TaskExecuteResponse,
    TaskUpdateRequest, TaskLogsResponse, LogEntry, APIResponse,
    ImagesListResponse, ImageInfo, SourceFileResponse, SourceFileUpdateRequest,
    LoginQrcodeResponse, LoginStatusResponse, LoginConfirmResponse
)
from app.api.dependencies import get_dispatcher
from app.api.utils import task_info_to_response
from app.api.exceptions import (
    TaskNotFoundError,
    AccountExistsError,
    LicenseExpiredError,
    TaskLimitReachedError,
)
from app.manager.task_dispatcher import TaskDispatcher
from app.manager.task_info import TaskStatus
from app.core.logger import logger
from app.core.license_manager import get_license_manager, LicenseManager
from app.utils.path_utils import get_user_images_path, get_user_source_file_path

router = APIRouter()


@router.post("/", response_model=TaskCreateResponse, tags=["任务管理"])
async def create_task(
    request: TaskCreateRequest,
    dispatcher: TaskDispatcher = Depends(get_dispatcher),
    license_manager: LicenseManager = Depends(get_license_manager),
):
    """
    创建新任务
    
    创建一个新的任务，如果账户ID已存在任务则返回错误
    """
    try:
        # ---------------- 注册码与任务数量限制 ----------------
        # 当前任务数 & 最大任务数（已过期时将退回免费版上限）
        current_count = len(dispatcher.list_tasks())
        max_tasks = license_manager.get_max_tasks()

        if current_count >= max_tasks:
            if not license_manager.is_activated():
                # 免费试用：只提示，不弹激活框
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"免费试用版最多只能创建 {max_tasks} 个任务。请激活产品以创建更多任务。",
                    headers={"X-License-Limit": "free_trial"},
                )
            else:
                # 已激活：使用专用异常，前端可引导查看套餐
                raise TaskLimitReachedError(
                    max_tasks=max_tasks,
                    current_tasks=current_count,
                    remaining=0,
                )

        # ---------------- 准备参数 ----------------
        kwargs = request.dict(exclude={"sys_type"})
        
        # 处理 task_type：在接口层将字符串转换为枚举（确保类型正确）
        from app.data.constants import DEFAULT_TASK_TYPE
        task_type_str = kwargs.get('task_type', 'xhs_type')
        if isinstance(task_type_str, str):
            if task_type_str == 'xhs_type' or task_type_str == DEFAULT_TASK_TYPE.XHS_TYPE.value:
                kwargs['task_type'] = DEFAULT_TASK_TYPE.XHS_TYPE
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的任务类型: {task_type_str}"
                )
        # 如果已经是枚举类型，保持不变
        elif isinstance(task_type_str, DEFAULT_TASK_TYPE):
            kwargs['task_type'] = task_type_str
        else:
            kwargs['task_type'] = DEFAULT_TASK_TYPE.XHS_TYPE  # 默认值
        
        # 处理执行间隔限制
        interval_value = request.interval
        interval_limit = license_manager.get_interval_limit()
        if interval_limit is not None:
            # 未激活：强制固定为 2 小时
            if interval_value != interval_limit:
                logger.info("免费试用版：执行间隔已自动设置为2小时（7200秒）")
            interval_value = interval_limit
        else:
            # 已激活：校验范围（15分钟 - 3小时）
            if interval_value < 900 or interval_value > 10800:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="执行间隔必须在900秒（15分钟）到10800秒（3小时）之间",
                )
        kwargs["interval"] = interval_value
        
        # 处理 task_end_time
        if request.task_end_time:
            kwargs['task_end_time'] = date_type.fromisoformat(request.task_end_time)
        
        # 添加任务（此时 task_type 已经是枚举类型）
        task_id = await dispatcher.add_task(sys_type=request.sys_type, **kwargs)
        
        # 获取任务信息
        task_info = dispatcher.get_task_status(task_id)
        if not task_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="任务创建成功但无法获取任务信息"
            )
        
        return TaskCreateResponse(
            success=True,
            task_id=task_id,
            message="任务创建成功",
            task_info=task_info_to_response(task_info)
        )
    
    except ValueError as e:
        # 账户ID已存在或其他验证错误
        error_msg = str(e)
        if "已存在任务" in error_msg:
            # 提取已存在的任务ID
            parts = error_msg.split("'")
            if len(parts) >= 4:
                existing_task_id = parts[3]
                raise AccountExistsError(request.xhs_account_id, existing_task_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {str(e)}"
        )


@router.get("/", response_model=TaskListResponse, tags=["任务管理"])
async def list_tasks(
    account_id: Optional[str] = Query(None, description="过滤指定账户的任务"),
    status_filter: Optional[str] = Query(None, alias="status", description="过滤指定状态的任务"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    列出所有任务
    
    支持按账户ID和状态过滤，支持分页
    """
    try:
        # 获取任务列表
        tasks = dispatcher.list_tasks(account_id=account_id)
        
        # 按状态过滤
        if status_filter:
            try:
                status_enum = TaskStatus(status_filter)
                tasks = [t for t in tasks if t.status == status_enum]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的状态值: {status_filter}，有效值: {', '.join([s.value for s in TaskStatus])}"
                )
        
        # 分页
        total = len(tasks)
        tasks = tasks[offset:offset + limit]
        
        # 转换为响应模型
        task_responses = [task_info_to_response(task) for task in tasks]
        
        return TaskListResponse(
            total=total,
            tasks=task_responses
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务列表失败: {str(e)}"
        )


@router.get("/{task_id}", response_model=TaskInfoResponse, tags=["任务管理"])
async def get_task(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    获取任务详情
    
    根据任务ID获取任务的详细信息
    """
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    return task_info_to_response(task_info)


@router.delete("/{task_id}", response_model=APIResponse, tags=["任务管理"])
async def delete_task(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    删除任务
    
    删除指定的任务，如果任务正在运行，会先暂停再删除
    """
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        success = await dispatcher.remove_task(task_id)
        if success:
            return APIResponse(
                success=True,
                message="任务删除成功"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="任务删除失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除任务失败: {str(e)}"
        )


@router.patch("/{task_id}", response_model=TaskInfoResponse, tags=["任务管理"])
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    更新任务属性
    
    支持部分字段更新，只传入要修改的字段即可。
    如果任务正在运行，属性将在下一次执行时生效。
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        # 获取明确设置的字段（使用 exclude_unset 来区分"未传递"和"传递了 None"）
        request_dict = request.model_dump(exclude_unset=True)
        
        # 构建更新数据字典
        update_data = {}
        if 'user_query' in request_dict:
            update_data['user_query'] = request.user_query
        if 'user_topic' in request_dict:
            update_data['user_topic'] = request.user_topic
        if 'user_style' in request_dict:
            update_data['user_style'] = request.user_style
        if 'user_target_audience' in request_dict:
            update_data['user_target_audience'] = request.user_target_audience
        if 'task_end_time' in request_dict:
            update_data['task_end_time'] = request.task_end_time
        if 'interval' in request_dict:
            update_data['interval'] = request.interval
        # valid_time_range 可以是 None（无限制）或 [start_hour, end_hour]
        if 'valid_time_range' in request_dict:
            # 如果值为 None，表示设置为无限制
            if request.valid_time_range is None:
                update_data['valid_time_range'] = None
            # 如果提供了列表值，验证格式
            elif isinstance(request.valid_time_range, list):
                if len(request.valid_time_range) != 2:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="有效时间范围必须是 [start_hour, end_hour] 格式"
                    )
                if not (0 <= request.valid_time_range[0] < 24 and 0 <= request.valid_time_range[1] < 24):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="时间范围必须在 0-23 之间"
                    )
                if request.valid_time_range[0] >= request.valid_time_range[1]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="开始时间必须小于结束时间"
                    )
                update_data['valid_time_range'] = request.valid_time_range
        if 'mode' in request_dict:
            update_data['mode'] = request.mode
        if 'interaction_note_count' in request_dict:
            update_data['interaction_note_count'] = request.interaction_note_count
        
        # 检查是否有要更新的字段
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要提供一个要更新的字段"
            )
        
        # 执行更新
        success = await dispatcher.update_task(task_id, **update_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="任务更新失败"
            )
        
        # 获取更新后的任务信息
        updated_task_info = dispatcher.get_task_status(task_id)
        if not updated_task_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取更新后的任务信息失败"
            )
        
        return task_info_to_response(updated_task_info)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新任务失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新任务失败: {str(e)}"
        )


@router.post("/{task_id}/pause", response_model=APIResponse, tags=["任务管理"])
async def pause_task(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    暂停任务
    
    暂停指定任务的执行
    """
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        success = dispatcher.pause_task(task_id)
        if success:
            return APIResponse(
                success=True,
                message="任务暂停成功",
                data={
                    "task_id": task_id,
                    "status": "paused"
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="任务暂停失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"暂停任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"暂停任务失败: {str(e)}"
        )


@router.post("/{task_id}/resume", response_model=APIResponse, tags=["任务管理"])
async def resume_task(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    恢复任务
    
    恢复已暂停的任务
    """
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        success = dispatcher.resume_task(task_id)
        if success:
            # 获取更新后的任务信息
            updated_task_info = dispatcher.get_task_status(task_id)
            return APIResponse(
                success=True,
                message="任务恢复成功",
                data={
                    "task_id": task_id,
                    "status": updated_task_info.status.value if updated_task_info else "pending",
                    "next_execution_time": updated_task_info.next_execution_time.isoformat() if updated_task_info and updated_task_info.next_execution_time else None
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="任务恢复失败，请检查任务状态"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复任务失败: {str(e)}"
        )


@router.post("/{task_id}/reorder", response_model=APIResponse, tags=["任务管理"])
async def reorder_task(
    task_id: str,
    request: TaskReorderRequest,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    调整任务优先级
    
    通过修改 next_execution_time 来调整任务的执行优先级
    """
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        success = dispatcher.reorder_task(task_id, request.priority_offset)
        if success:
            # 获取更新后的任务信息
            updated_task_info = dispatcher.get_task_status(task_id)
            return APIResponse(
                success=True,
                message="任务优先级调整成功",
                data={
                    "task_id": task_id,
                    "new_next_execution_time": updated_task_info.next_execution_time.isoformat() if updated_task_info and updated_task_info.next_execution_time else None
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="任务优先级调整失败"
            )
    except ValueError as e:
        # 任务正在运行、已暂停等错误
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"调整任务优先级失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"调整任务优先级失败: {str(e)}"
        )


@router.post("/{task_id}/execute", response_model=TaskExecuteResponse, tags=["任务管理"])
async def execute_task(
    task_id: str,
    request: Optional[TaskExecuteRequest] = Body(None, description="执行任务请求参数（可选）"),
    dispatcher: TaskDispatcher = Depends(get_dispatcher),
    license_manager: LicenseManager = Depends(get_license_manager),
):
    """
    立即执行任务
    
    立即执行指定任务，不等待调度器的正常调度。适用于用户临时需要执行任务的场景。
    
    - 任务会立即开始执行
    - 使用全局锁确保同一时间只有一个任务执行（避免 cookie 冲突）
    - 如果任务正在执行中，会返回错误
    - 执行完成后，可选择是否更新下次执行时间（默认会更新，基于当前时间重新计算）
    
    请求体可选，如果不提供，则使用默认参数（update_next_execution_time=True）
    
    示例请求体：
    ```json
    {
        "update_next_execution_time": true
    }
    ```
    """
    # 注册码限制：未激活/过期时不允许立即执行
    if not license_manager.can_execute_immediately():
        # 这里不区分免费试用和已过期，统一文案即可
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前版本不支持立即执行功能，请激活或续费产品以使用此功能。",
            headers={"X-License-Limit": "free_trial"},
        )

    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    # 如果未提供请求体，使用默认值
    update_next_execution_time = request.update_next_execution_time if request else True
    
    try:
        # 执行任务
        execution_result = await dispatcher.execute_task_immediately(
            task_id=task_id,
            update_next_execution_time=update_next_execution_time
        )
        
        return TaskExecuteResponse(
            success=execution_result.get("success", True),
            message="任务执行成功" if execution_result.get("success", True) else "任务执行失败",
            task_id=execution_result["task_id"],
            execution_start_time=execution_result["execution_start_time"],
            execution_end_time=execution_result["execution_end_time"],
            duration_seconds=execution_result["duration_seconds"],
            should_continue=execution_result["should_continue"],
            next_execution_time=execution_result.get("next_execution_time")
        )
    
    except ValueError as e:
        # 任务不存在、已完成、正在执行等错误
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        # 任务执行失败
        logger.error(f"任务立即执行失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"立即执行任务失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"立即执行任务失败: {str(e)}"
        )


@router.get("/{task_id}/logs", response_model=TaskLogsResponse, tags=["任务管理"])
async def get_task_logs(
    task_id: str,
    since: Optional[str] = Query(None, description="只返回此时间之后的日志（ISO 格式）", examples=["2026-01-10T10:00:00"]),
    level: Optional[str] = Query(None, description="日志级别过滤（多个级别用逗号分隔）", examples=["INFO,ERROR"]),
    limit: Optional[int] = Query(100, description="最多返回的日志条数", ge=1, le=1000),
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    获取任务日志
    
    获取指定任务的执行日志，支持时间过滤、级别过滤和数量限制。
    
    - `since`: 可选，只返回此时间之后的日志（ISO 格式，如 "2026-01-10T10:00:00"）
    - `level`: 可选，日志级别过滤（多个级别用逗号分隔，如 "INFO,ERROR"）
    - `limit`: 可选，最多返回的日志条数（默认100，最大1000）
    
    返回的日志按时间顺序排列（从旧到新）。
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        from app.utils.task_log_collector import get_task_log_collector
        from app.data.constants import LogBindType
        from datetime import datetime
        
        collector = get_task_log_collector()
        
        # 解析 since 参数
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except (ValueError, TypeError) as e:
                logger.warning(f"无法解析 since 参数: {since}, error: {e}")
                since_dt = None
        
        # 解析 level 过滤参数
        level_filter = None
        if level:
            level_filter = [l.strip().upper() for l in level.split(',') if l.strip()]
            # 验证级别是否有效
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            level_filter = [l for l in level_filter if l in valid_levels]
            if not level_filter:
                level_filter = None
        
        # 获取日志（只获取 task_log 类型的日志，前端只展示这种类型）
        # 获取 limit+1 条，如果实际返回了 limit+1 条，说明还有更多
        logs = await collector.get_logs_async(
            task_id=task_id,
            bindtype=LogBindType.TASK_LOG,
            since=since_dt,
            level_filter=level_filter,
            limit=limit + 1 if limit else None
        )
        
        # 判断是否还有更多日志
        has_more = False
        if limit and len(logs) > limit:
            has_more = True
            logs = logs[-limit:]  # 只返回最新的 limit 条
        
        total_count = collector.get_log_count(task_id, bindtype=LogBindType.TASK_LOG)
        
        # 转换为响应模型
        log_entries = [LogEntry(**log) for log in logs]
        
        return TaskLogsResponse(
            success=True,
            task_id=task_id,
            logs=log_entries,
            total=total_count,
            has_more=has_more,
            message=f"成功获取 {len(log_entries)} 条日志"
        )
    
    except Exception as e:
        logger.error(f"获取任务日志失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务日志失败: {str(e)}"
        )


@router.get("/{task_id}/resources/images", response_model=ImagesListResponse, tags=["资源管理"])
async def get_task_images(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    获取任务图片列表
    
    返回任务生成的所有图片文件列表
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        account_id = task_info.account_id
        images_dir = get_user_images_path(account_id)
        
        # 检查目录是否存在
        if not os.path.exists(images_dir):
            return ImagesListResponse(images=[])
        
        # 获取所有图片文件
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        images = []
        
        for filename in os.listdir(images_dir):
            file_path = os.path.join(images_dir, filename)
            if os.path.isfile(file_path):
                file_ext = Path(filename).suffix.lower()
                if file_ext in image_extensions:
                    # 获取文件信息
                    stat = os.stat(file_path)
                    modified_time = None
                    try:
                        from datetime import datetime
                        modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    except:
                        pass
                    
                    images.append(ImageInfo(
                        filename=filename,
                        url=f"/api/v1/tasks/{task_id}/resources/images/{filename}",
                        size=stat.st_size,
                        modified_time=modified_time
                    ))
        
        # 按修改时间倒序排列（最新的在前）
        images.sort(key=lambda x: x.modified_time or "", reverse=True)
        
        return ImagesListResponse(images=images)
    
    except Exception as e:
        logger.error(f"获取任务图片列表失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务图片列表失败: {str(e)}"
        )


@router.get("/{task_id}/resources/images/{filename}", tags=["资源管理"], include_in_schema=False)
async def get_task_image(
    task_id: str,
    filename: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    获取任务图片文件
    
    返回指定图片文件
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        account_id = task_info.account_id
        images_dir = get_user_images_path(account_id)
        file_path = os.path.join(images_dir, filename)
        
        # 安全检查：确保文件在 images 目录内
        if not os.path.abspath(file_path).startswith(os.path.abspath(images_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="禁止访问此文件"
            )
        
        # 检查文件是否存在
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"图片文件不存在: {filename}"
            )
        
        return FileResponse(
            file_path,
            media_type="image/png" if filename.lower().endswith('.png') else "image/jpeg",
            filename=filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务图片失败: task_id={task_id}, filename={filename}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务图片失败: {str(e)}"
        )


@router.get("/{task_id}/resources/source", response_model=SourceFileResponse, tags=["资源管理"])
async def get_task_source_file(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    获取任务知识库文件
    
    返回任务的 knowledge base 文件内容
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        account_id = task_info.account_id
        source_file_path = get_user_source_file_path(account_id, 'text.md')
        
        # 检查文件是否存在
        if not os.path.exists(source_file_path):
            # 如果文件不存在，返回空内容
            return SourceFileResponse(
                content="",
                filename="text.md",
                size=0,
                modified_time=None
            )
        
        # 读取文件内容
        with open(source_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 获取文件信息
        stat = os.stat(source_file_path)
        modified_time = None
        try:
            from datetime import datetime
            modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except:
            pass
        
        return SourceFileResponse(
            content=content,
            filename="text.md",
            size=stat.st_size,
            modified_time=modified_time
        )
    
    except Exception as e:
        logger.error(f"获取任务知识库文件失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务知识库文件失败: {str(e)}"
        )


@router.put("/{task_id}/resources/source", response_model=APIResponse, tags=["资源管理"])
async def update_task_source_file(
    task_id: str,
    request: SourceFileUpdateRequest,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    更新任务知识库文件
    
    更新任务的 knowledge base 文件内容
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        account_id = task_info.account_id
        source_file_path = get_user_source_file_path(account_id, 'text.md')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(source_file_path), exist_ok=True)
        
        # 写入文件内容
        with open(source_file_path, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        logger.info(f"任务 {task_id} 知识库文件更新成功")
        
        return APIResponse(
            success=True,
            message="知识库文件更新成功"
        )
    
    except Exception as e:
        logger.error(f"更新任务知识库文件失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新任务知识库文件失败: {str(e)}"
        )


@router.get("/{task_id}/resources/source/download", tags=["资源管理"])
async def download_task_source_file(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    下载任务知识库文件
    
    下载任务的 knowledge base 文件
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        account_id = task_info.account_id
        source_file_path = get_user_source_file_path(account_id, 'text.md')
        
        # 检查文件是否存在
        if not os.path.exists(source_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识库文件不存在"
            )
        
        return FileResponse(
            source_file_path,
            media_type="text/markdown",
            filename="text.md"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载任务知识库文件失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载任务知识库文件失败: {str(e)}"
        )


@router.post("/{task_id}/resources/source/upload", response_model=APIResponse, tags=["资源管理"])
async def upload_task_source_file(
    task_id: str,
    file: UploadFile = File(...),
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    上传任务知识库文件
    
    上传并替换任务的 knowledge base 文件
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        account_id = task_info.account_id
        source_file_path = get_user_source_file_path(account_id, 'text.md')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(source_file_path), exist_ok=True)
        
        # 读取上传的文件内容
        content = await file.read()
        
        # 写入文件
        with open(source_file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"任务 {task_id} 知识库文件上传成功")
        
        return APIResponse(
            success=True,
            message="知识库文件上传成功"
        )
    
    except Exception as e:
        logger.error(f"上传任务知识库文件失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传任务知识库文件失败: {str(e)}"
        )


@router.get("/{task_id}/login/qrcode", response_model=LoginQrcodeResponse, tags=["登录管理"])
async def get_login_qrcode(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    获取任务登录二维码
    
    返回小红书登录二维码（base64编码），用于前端显示
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        # 获取 Agent 实例
        agent = task_info.task_manager.agent
        
        # 确保 MCP 连接已建立
        await agent.ensure_connected()
        
        # 获取登录二维码
        qrcode_info = await agent.get_login_qrcode()
        
        logger.debug(f"获取到的二维码信息: {list(qrcode_info.keys())}")
        
        # 优先使用 qrcode_url，如果没有则使用 base64_image 构建
        base64_image = qrcode_info.get("base64_image", "")
        qrcode_url = qrcode_info.get("qrcode_url", "")
        
        if not base64_image and not qrcode_url:
            logger.error(f"获取二维码失败：未返回二维码图片，返回信息: {qrcode_info}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取二维码失败：未返回二维码图片"
            )
        
        # 如果没有 qrcode_url，使用 base64_image 构建
        if not qrcode_url and base64_image:
            qrcode_url = f"data:image/png;base64,{base64_image}"
        
        return LoginQrcodeResponse(
            qrcode_base64=base64_image,
            qrcode_url=qrcode_url,
            timeout=qrcode_info.get("timeout", 180),
            message=qrcode_info.get("message", "请使用小红书App扫描二维码登录")
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        # MCP客户端未连接的错误
        if "未连接" in str(e) or "connect()" in str(e):
            logger.warning(f"MCP客户端未连接，尝试重新连接: task_id={task_id}")
            try:
                # 强制重新连接
                agent.is_connected = False
                await agent.ensure_connected()
                # 重试获取二维码
                qrcode_info = await agent.get_login_qrcode()
                
                base64_image = qrcode_info.get("base64_image", "")
                qrcode_url = qrcode_info.get("qrcode_url", "")
                
                if not base64_image and not qrcode_url:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="获取二维码失败：未返回二维码图片"
                    )
                
                if not qrcode_url and base64_image:
                    qrcode_url = f"data:image/png;base64,{base64_image}"
                
                return LoginQrcodeResponse(
                    qrcode_base64=base64_image,
                    qrcode_url=qrcode_url,
                    timeout=qrcode_info.get("timeout", 180),
                    message=qrcode_info.get("message", "请使用小红书App扫描二维码登录")
                )
            except Exception as retry_error:
                logger.error(f"重新连接后获取二维码失败: task_id={task_id}, error={retry_error}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取登录二维码失败: {str(retry_error)}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"参数错误: {str(e)}"
            )
    except Exception as e:
        logger.error(f"获取登录二维码失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取登录二维码失败: {str(e)}"
        )


@router.get("/{task_id}/login/status", response_model=LoginStatusResponse, tags=["登录管理"])
async def get_login_status(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    检查任务登录状态
    
    检查小红书账号是否已登录
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        # 获取 Agent 实例
        agent = task_info.task_manager.agent
        
        # 确保 MCP 连接已建立
        await agent.ensure_connected()
        
        # 检查登录状态
        status_info = await agent.check_login_status()
        
        return LoginStatusResponse(
            is_logged_in=status_info.get("is_logged_in", False),
            message=status_info.get("message", "未知状态")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查登录状态失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查登录状态失败: {str(e)}"
        )


@router.post("/{task_id}/login/confirm", response_model=LoginConfirmResponse, tags=["登录管理"])
async def confirm_login(
    task_id: str,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """
    确认登录
    
    检查登录状态并返回结果，用于用户扫码后确认登录
    """
    # 检查任务是否存在
    task_info = dispatcher.get_task_status(task_id)
    if not task_info:
        raise TaskNotFoundError(task_id)
    
    try:
        # 获取 Agent 实例
        agent = task_info.task_manager.agent
        
        # 确保 MCP 连接已建立
        await agent.ensure_connected()
        
        # 检查登录状态
        status_info = await agent.check_login_status()
        
        is_logged_in = status_info.get("is_logged_in", False)
        
        return LoginConfirmResponse(
            success=True,
            is_logged_in=is_logged_in,
            message="登录成功" if is_logged_in else "登录失败，请重新扫码"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认登录失败: task_id={task_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"确认登录失败: {str(e)}"
        )

