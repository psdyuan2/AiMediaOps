"""
健康检查路由
"""

from datetime import datetime
from fastapi import APIRouter
from app.api.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["健康检查"])
async def health_check():
    """
    健康检查接口
    
    返回 API 服务状态
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )

