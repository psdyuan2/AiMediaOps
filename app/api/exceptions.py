"""
API 异常处理模块

定义自定义异常和异常处理器
"""

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi import Request
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
            "message": str(exc) if logger.level <= 10 else "请查看服务器日志"
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP 异常处理器
    
    处理 FastAPI 的 HTTPException
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail
        }
    )

