"""
API 数据模型定义

使用 Pydantic 定义请求和响应模型
"""

from typing import Optional, List, Any, Dict
from datetime import datetime, date
from pydantic import BaseModel, Field
from app.data.constants import TaskMode


# ==================== 请求模型 ====================

class TaskCreateRequest(BaseModel):
    """创建任务请求模型"""
    sys_type: str = Field(..., description="操作系统类型", example="mac_intel")
    task_type: str = Field(default="xhs_type", description="任务类型", example="xhs_type")
    xhs_account_id: str = Field(..., description="小红书账户ID", example="account_1")
    xhs_account_name: str = Field(..., description="小红书账户名称", example="账号1")
    user_query: Optional[str] = Field(None, description="用户查询内容", example="开始运营")
    user_topic: Optional[str] = Field(None, description="帖子主题", example="科技")
    user_style: Optional[str] = Field(None, description="内容风格", example="专业")
    user_target_audience: Optional[str] = Field(None, description="目标受众", example="技术爱好者")
    task_end_time: Optional[str] = Field(None, description="任务结束时间（ISO日期格式）", example="2026-02-08")
    interval: Optional[int] = Field(default=3600, description="执行间隔（秒）", example=3600)
    valid_time_range: Optional[List[int]] = Field(default=[8, 22], description="有效时间范围 [开始小时, 结束小时]", example=[8, 22])
    mode: Optional[str] = Field(default=TaskMode.STANDARD.value, description="任务执行模式", examples=["standard", "interaction", "publish"])
    interaction_note_count: Optional[int] = Field(default=3, description="互动笔记数量", example=3, ge=1, le=5)
    
    class Config:
        json_schema_extra = {
            "example": {
                "sys_type": "mac_intel",
                "task_type": "xhs_type",
                "xhs_account_id": "account_1",
                "xhs_account_name": "账号1",
                "user_query": "开始运营",
                "user_topic": "科技",
                "user_style": "专业",
                "user_target_audience": "技术爱好者",
                "task_end_time": "2026-02-08",
                "interval": 3600,
                "valid_time_range": [8, 22]
            }
        }


class TaskReorderRequest(BaseModel):
    """调整任务优先级请求模型"""
    priority_offset: int = Field(..., description="优先级偏移量（秒），正数延后，负数提前", example=-1800)
    
    class Config:
        json_schema_extra = {
            "example": {
                "priority_offset": -1800
            }
        }


class TaskUpdateRequest(BaseModel):
    """更新任务请求模型"""
    user_query: Optional[str] = Field(None, description="用户查询内容", example="开始运营")
    user_topic: Optional[str] = Field(None, description="帖子主题", example="科技")
    user_style: Optional[str] = Field(None, description="内容风格", example="专业")
    user_target_audience: Optional[str] = Field(None, description="目标受众", example="技术爱好者")
    task_end_time: Optional[str] = Field(None, description="任务结束时间（ISO日期格式）", example="2026-02-08")
    interval: Optional[int] = Field(None, description="执行间隔（秒）", example=3600, ge=60)
    valid_time_range: Optional[List[int]] = Field(None, description="有效时间范围 [开始小时, 结束小时]，None 表示无限制", example=[8, 22])
    mode: Optional[str] = Field(None, description="任务执行模式", examples=["standard", "interaction", "publish"])
    interaction_note_count: Optional[int] = Field(None, description="互动笔记数量", example=3, ge=1, le=5)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_topic": "科技",
                "user_style": "专业",
                "user_target_audience": "技术爱好者",
                "task_end_time": "2026-02-08",
                "interval": 3600,
                "valid_time_range": [8, 22]
            }
        }


class SourceFileUpdateRequest(BaseModel):
    """知识库文件更新请求模型"""
    content: str = Field(..., description="文件内容", example="# Knowledge Base\n\nContent here...")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "# Knowledge Base\n\nContent here..."
            }
        }


class ImageInfo(BaseModel):
    """图片信息模型"""
    filename: str = Field(..., description="文件名", example="image.png")
    url: str = Field(..., description="图片URL", example="/api/v1/tasks/{task_id}/resources/images/image.png")
    size: Optional[int] = Field(None, description="文件大小（字节）", example=102400)
    modified_time: Optional[str] = Field(None, description="修改时间（ISO格式）", example="2026-01-11T19:06:16")


class ImagesListResponse(BaseModel):
    """图片列表响应模型"""
    images: List[ImageInfo] = Field(..., description="图片列表")


class SourceFileResponse(BaseModel):
    """知识库文件响应模型"""
    content: str = Field(..., description="文件内容")
    filename: str = Field(..., description="文件名", example="text.md")
    size: Optional[int] = Field(None, description="文件大小（字节）", example=10240)
    modified_time: Optional[str] = Field(None, description="修改时间（ISO格式）", example="2026-01-11T19:06:16")


class LoginQrcodeResponse(BaseModel):
    """登录二维码响应模型"""
    qrcode_base64: str = Field(..., description="二维码图片（base64编码）", example="iVBORw0KGgoAAAANS...")
    qrcode_url: str = Field(..., description="二维码图片URL（data URI）", example="data:image/png;base64,iVBORw0KGgoAAAANS...")
    timeout: Optional[int] = Field(None, description="二维码超时时间（秒）", example=180)
    message: Optional[str] = Field(None, description="提示信息", example="请使用小红书App扫描二维码登录")


class LoginStatusResponse(BaseModel):
    """登录状态响应模型"""
    is_logged_in: bool = Field(..., description="是否已登录", example=True)
    message: str = Field(..., description="状态消息", example="已登录")


class LoginConfirmResponse(BaseModel):
    """登录确认响应模型"""
    success: bool = Field(..., description="是否成功", example=True)
    is_logged_in: bool = Field(..., description="是否已登录", example=True)
    message: str = Field(..., description="状态消息", example="登录成功")


class TaskExecuteRequest(BaseModel):
    """立即执行任务请求模型"""
    update_next_execution_time: bool = Field(True, description="是否更新下次执行时间（默认为 True，基于当前时间重新计算）", example=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "update_next_execution_time": True
            }
        }


# ==================== 响应模型 ====================

class APIResponse(BaseModel):
    """标准 API 响应模型"""
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
    data: Optional[Any] = Field(None, description="响应数据")


class TaskInfoResponse(BaseModel):
    """任务信息响应模型"""
    task_id: str = Field(..., description="任务ID")
    account_id: str = Field(..., description="账户ID")
    account_name: str = Field(..., description="账户名称")
    task_type: str = Field(..., description="任务类型")
    status: str = Field(..., description="任务状态")
    interval: int = Field(..., description="执行间隔（秒）")
    valid_time_range: Optional[List[int]] = Field(None, description="有效时间范围 [开始小时, 结束小时]，None 表示无限制")
    task_end_time: str = Field(..., description="任务结束时间")
    last_execution_time: Optional[str] = Field(None, description="上次执行时间")
    next_execution_time: Optional[str] = Field(None, description="下次执行时间")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    round_num: Optional[int] = Field(None, description="执行轮次")
    mode: str = Field(..., description="任务执行模式", example="standard")
    interaction_note_count: int = Field(..., description="互动笔记数量", example=3)
    kwargs: Optional[Dict[str, Any]] = Field(None, description="任务参数")
    login_status: Optional[bool] = Field(None, description="登录状态：True=已登录，False=未登录，None=未知")
    login_status_checked_at: Optional[str] = Field(None, description="登录状态检查时间")


class TaskCreateResponse(BaseModel):
    """创建任务响应模型"""
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")
    task_info: Optional[TaskInfoResponse] = Field(None, description="任务信息")


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    total: int = Field(..., description="任务总数")
    tasks: List[TaskInfoResponse] = Field(..., description="任务列表")


class TaskExecuteResponse(BaseModel):
    """立即执行任务响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    task_id: str = Field(..., description="任务ID")
    execution_start_time: str = Field(..., description="执行开始时间")
    execution_end_time: str = Field(..., description="执行结束时间")
    duration_seconds: float = Field(..., description="执行耗时（秒）")
    should_continue: bool = Field(..., description="任务是否应继续执行")
    next_execution_time: Optional[str] = Field(None, description="下次执行时间（如果更新了）")


class DispatcherStatusResponse(BaseModel):
    """调度器状态响应模型"""
    is_running: bool = Field(..., description="是否正在运行")
    total_tasks: int = Field(..., description="任务总数")
    pending_tasks: int = Field(..., description="等待执行的任务数")
    running_tasks: int = Field(..., description="正在运行的任务数")
    paused_tasks: int = Field(..., description="已暂停的任务数")
    completed_tasks: int = Field(..., description="已完成的任务数")
    error_tasks: int = Field(..., description="错误任务数")
    current_running_task: Optional[Dict[str, Any]] = Field(None, description="当前运行的任务")


class LogEntry(BaseModel):
    """日志条目响应模型"""
    timestamp: str = Field(..., description="时间戳")
    level: str = Field(..., description="日志级别")
    module: str = Field(..., description="模块名")
    function: str = Field(..., description="函数名")
    message: str = Field(..., description="日志消息")
    task_id: Optional[str] = Field(None, description="任务ID")


class TaskLogsResponse(BaseModel):
    """任务日志响应模型"""
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    logs: List[LogEntry] = Field(..., description="日志列表")
    total: int = Field(..., description="总日志条数")
    has_more: bool = Field(False, description="是否还有更多日志")
    message: Optional[str] = Field(None, description="响应消息")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="状态", example="healthy")
    timestamp: str = Field(..., description="时间戳")
    version: str = Field(..., description="版本号")

