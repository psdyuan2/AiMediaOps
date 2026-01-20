"""
API 异常处理模块

定义自定义异常和异常处理器
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.logger import logger


class TaskNotFoundError(HTTPException):
    """任务不存在异常"""
    def __init__(self, task_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )


class AccountExistsError(HTTPException):
    """账户已存在异常"""
    def __init__(self, account_id: str, existing_task_id: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"账户ID '{account_id}' 已存在任务 '{existing_task_id}'，同一账户不能创建多个任务"
        )


class DispatcherNotRunningError(HTTPException):
    """调度器未运行异常"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="调度器未运行"
        )


class DispatcherAlreadyRunningError(HTTPException):
    """调度器已运行异常"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="调度器已在运行"
        )


class LicenseNotActivatedError(HTTPException):
    """产品未激活异常"""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="产品未激活，请先激活注册码",
        )


class LicenseExpiredError(HTTPException):
    """产品已过期异常"""

    def __init__(self, end_time: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"产品已过期，过期时间：{end_time}。请重新激活注册码",
        )


class TaskLimitReachedError(HTTPException):
    """任务数量达到上限异常"""

    def __init__(self, max_tasks: int, current_tasks: int, remaining: int):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"已达到最大任务数量限制（{max_tasks}），无法创建新任务。"
                f"当前任务数：{current_tasks}，剩余可用：{remaining}"
            ),
        )


async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器
    
    捕获所有未处理的异常，返回标准格式的错误响应
    """
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "内部服务器错误",
            "message": str(exc),
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP 异常处理器
    
    处理 FastAPI 的 HTTPException，返回统一格式，并在需要时附加错误代码。
    """
    error_data = {
        "success": False,
        "error": exc.detail,
    }

    # 根据异常类型附加错误代码和类型，便于前端处理
    if isinstance(exc, LicenseNotActivatedError):
        error_data["error_code"] = "LICENSE_NOT_ACTIVATED"
        error_data["error_type"] = "license"
    elif isinstance(exc, LicenseExpiredError):
        error_data["error_code"] = "LICENSE_EXPIRED"
        error_data["error_type"] = "license"
    elif isinstance(exc, TaskLimitReachedError):
        error_data["error_code"] = "TASK_LIMIT_REACHED"
        error_data["error_type"] = "task_limit"

    return JSONResponse(
        status_code=exc.status_code,
        content=error_data,
    )

