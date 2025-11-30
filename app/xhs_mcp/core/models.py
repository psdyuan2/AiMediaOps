"""
核心数据模型定义

使用 Pydantic v2 定义浏览器实例、配置文件和账户的数据结构。
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


class BrowserInstanceStatus(str, Enum):
    """浏览器实例状态"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class BrowserFingerprint(BaseModel):
    """浏览器指纹配置"""
    model_config = ConfigDict(extra="forbid")

    user_agent: str = Field(description="User-Agent 字符串")
    viewport: Dict[str, int] = Field(
        default_factory=lambda: {"width": 1920, "height": 1080},
        description="视口尺寸"
    )
    language: str = Field(default="zh-CN", description="浏览器语言")
    timezone: str = Field(default="Asia/Shanghai", description="时区")
    platform: str = Field(default="Win32", description="平台")
    hardware_concurrency: int = Field(default=8, description="硬件并发数")
    device_memory: int = Field(default=8, description="设备内存(GB)")

    # Canvas 指纹
    canvas_fingerprint: Optional[str] = Field(default=None, description="Canvas 指纹")

    # WebGL 指纹
    webgl_vendor: str = Field(default="Google Inc.", description="WebGL 厂商")
    webgl_renderer: str = Field(default="ANGLE (Intel, Intel(R) UHD Graphics 630 (0x000059A2) Direct3D11 vs_5_0 ps_5_0, D3D11)", description="WebGL 渲染器")

    # Audio 指纹
    audio_fingerprint: Optional[str] = Field(default=None, description="音频指纹")


class BrowserProfile(BaseModel):
    """浏览器配置文件"""
    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(default_factory=lambda: str(uuid4()), description="配置文件ID")
    name: str = Field(description="配置名称")
    fingerprint: BrowserFingerprint = Field(description="浏览器指纹")

    # 浏览器启动参数
    headless: bool = Field(default=False, description="是否无头模式")
    slow_mo: int = Field(default=100, description="操作延迟(ms)")
    user_data_dir: Optional[str] = Field(default=None, description="用户数据目录")

    # 代理设置
    proxy: Optional[Dict[str, str]] = Field(default=None, description="代理设置")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class XHSAccount(BaseModel):
    """小红书账户信息"""
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(default_factory=lambda: str(uuid4()), description="账户ID")
    username: str = Field(description="用户名")
    nickname: Optional[str] = Field(default=None, description="昵称")

    # 登录状态
    is_logged_in: bool = Field(default=False, description="是否已登录")
    last_login: Optional[datetime] = Field(default=None, description="最后登录时间")

    # 关联的浏览器实例
    browser_instance_id: Optional[str] = Field(default=None, description="关联的浏览器实例ID")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class BrowserInstance(BaseModel):
    """浏览器实例"""
    model_config = ConfigDict(extra="forbid")

    instance_id: str = Field(default_factory=lambda: str(uuid4()), description="实例ID")
    profile: BrowserProfile = Field(description="浏览器配置")

    # 状态信息
    status: BrowserInstanceStatus = Field(default=BrowserInstanceStatus.CREATED, description="实例状态")
    current_url: Optional[str] = Field(default=None, description="当前URL")

    # 关联的账户
    account: Optional[XHSAccount] = Field(default=None, description="关联的账户")

    # 性能统计
    start_time: Optional[datetime] = Field(default=None, description="启动时间")
    request_count: int = Field(default=0, description="请求计数")

    # 会话信息
    cookies: Dict[str, Any] = Field(default_factory=dict, description="Cookie 信息")
    local_storage: Dict[str, Any] = Field(default_factory=dict, description="本地存储")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")