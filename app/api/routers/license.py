"""
注册码相关路由
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.license_manager import LicenseManager, get_license_manager
from app.api.dependencies import get_dispatcher
from app.manager.task_dispatcher import TaskDispatcher
from app.core.logger import logger


router = APIRouter()


@router.get("/license/status", tags=["注册码"])
async def get_license_status(
    license_manager: LicenseManager = Depends(get_license_manager),
    dispatcher: TaskDispatcher = Depends(get_dispatcher),
) -> Dict[str, Any]:
    """
    获取当前激活状态和配置信息
    """
    # 当前任务数 & 最大任务数
    current_tasks = len(dispatcher.list_tasks())
    max_tasks = license_manager.get_max_tasks()
    remaining = max(0, max_tasks - current_tasks)

    activated = license_manager.is_activated()
    expired = activated and license_manager.is_expired()
    config = license_manager.get_config()

    # 未激活视为免费试用
    if not activated:
        return {
            "success": True,
            "activated": False,
            "expired": False,
            "config": None,
            "remaining_tasks": remaining,
            "current_tasks": current_tasks,
            "max_tasks": max_tasks,
            "is_free_trial": True,
        }

    return {
        "success": True,
        "activated": activated,
        "expired": expired,
        "config": config,
        "remaining_tasks": remaining,
        "current_tasks": current_tasks,
        "max_tasks": max_tasks,
        "is_free_trial": False,
    }


@router.post("/license/activate", tags=["注册码"])
async def activate_license(
    payload: Dict[str, str],
    license_manager: LicenseManager = Depends(get_license_manager),
) -> Dict[str, Any]:
    """
    激活注册码

    请求体:
    {
        "license_code": "your_license_code_here"
    }
    """
    license_code = (payload.get("license_code") or "").strip()
    if not license_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="license_code 不能为空",
        )

    try:
        result = await license_manager.activate(license_code)
        return {
            "success": True,
            "message": "激活成功",
            "config": result.get("config"),
        }
    except ValueError as e:
        # 注册码无效或已过期
        logger.warning(f"激活失败，注册码无效: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="注册码无效或已过期",
        )
    except RuntimeError as e:
        logger.error(f"激活失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"激活时发生未知错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="激活失败，请稍后重试",
        )

