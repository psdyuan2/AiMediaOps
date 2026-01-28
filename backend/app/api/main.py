"""
FastAPI 应用主入口

任务调度器 Web API 服务
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
from app.api.routers import health, dispatcher, tasks, accounts, help, license
from app.api.exceptions import (
    global_exception_handler,
    http_exception_handler
)
from app.core.logger import logger
import asyncio

# 创建 FastAPI 应用
app = FastAPI(
    title="任务调度器 API",
    description="任务调度器 Web API 接口，提供完整的任务管理功能",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 长请求超时处理中间件
class LongRequestMiddleware(BaseHTTPMiddleware):
    """
    处理长请求的中间件
    
    对于执行任务的请求，增加超时时间，确保任务能够完成。
    """
    
    async def dispatch(self, request: StarletteRequest, call_next):
        # 对于任务执行相关的请求，使用更长的超时时间
        if request.url.path.endswith("/execute"):
            # 使用 asyncio.wait_for 增加超时时间（30分钟）
            try:
                response = await asyncio.wait_for(
                    call_next(request),
                    timeout=1800.0  # 30分钟超时
                )
                return response
            except asyncio.TimeoutError:
                logger.error(f"请求超时: {request.url.path}")
                return JSONResponse(
                    status_code=504,
                    content={
                        "success": False,
                        "error": "请求超时",
                        "detail": "任务执行时间过长，已超过30分钟限制"
                    }
                )
        else:
            # 其他请求正常处理
            return await call_next(request)

# 添加长请求中间件（需要在 CORS 之前）
app.add_middleware(LongRequestMiddleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Vite 默认端口
        "http://localhost:5173",  # Vite 备用端口
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # 开发环境允许所有来源，生产环境应限制为具体域名
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全局异常处理器
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# 处理 Starlette 404 错误（确保返回 JSON 而不是 HTML）
@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """处理 Starlette HTTP 异常（包括 404），确保返回 JSON 格式"""
    if exc.status_code == 404:
        # 如果请求的是 API 路径，返回 JSON
        if request.url.path.startswith('/api/'):
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "接口不存在",
                    "detail": f"路径不存在: {request.url.path}"
                }
            )
        # 其他路径也返回 JSON（统一格式）
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": "页面不存在",
                "detail": f"路径不存在: {request.url.path}"
            }
        )
    # 其他 HTTP 状态码，转换为 HTTPException 由 http_exception_handler 处理
    raise HTTPException(status_code=exc.status_code, detail=exc.detail)

# 处理请求验证错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误，返回 JSON 格式"""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "请求参数验证失败",
            "detail": exc.errors()
        }
    )

# 注册路由
app.include_router(health.router, prefix="/api/v1", tags=["健康检查"])
app.include_router(dispatcher.router, prefix="/api/v1/dispatcher", tags=["调度器管理"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["任务管理"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["账户管理"])
app.include_router(help.router, prefix="/api/v1", tags=["帮助文档"])
app.include_router(license.router, prefix="/api/v1", tags=["注册码"])

# 静态文件服务
from pathlib import Path

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.get("/", tags=["根路径"], include_in_schema=False)
    async def index():
        """返回 Web 测试页面"""
        return FileResponse(str(static_dir / "index.html"))


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("任务调度器 API 服务启动")

    # 在启动时检查注册码状态，仅记录日志，不阻塞启动
    try:
        from app.core.license_manager import get_license_manager

        lm = get_license_manager()
        if not lm.is_activated():
            logger.warning("⚠️ 产品未激活，当前处于免费试用模式（最多 1 个任务，间隔固定 2 小时，不支持立即执行）")
        elif lm.is_expired():
            logger.warning("⚠️ 产品注册码已过期，请尽快重新激活")
        else:
            logger.info("✅ 产品注册码状态正常")
    except Exception as e:
        logger.error(f"启动时检查注册码状态失败: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("任务调度器 API 服务关闭")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

