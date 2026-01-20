# 任务调度器 Web API 接口设计方案

## 一、概述

### 1.1 目标
为 TaskDispatcher 构建基于 FastAPI 的 Web 接口，提供完整的任务管理功能，支持：
- 任务的增删改查
- 任务的暂停/恢复
- 任务优先级调整
- 调度器状态管理
- 实时任务状态查询

### 1.2 技术栈
- **框架**: FastAPI
- **异步支持**: 原生支持 async/await
- **数据验证**: Pydantic
- **API 文档**: 自动生成 Swagger/OpenAPI 文档
- **依赖管理**: 与现有 TaskDispatcher 集成

## 二、API 设计

### 2.1 基础信息

- **Base URL**: `/api/v1`
- **Content-Type**: `application/json`
- **响应格式**: JSON

### 2.2 路由设计

```
/api/v1/
├── /health                    # 健康检查
├── /dispatcher/
│   ├── /status               # 获取调度器状态
│   ├── /start                # 启动调度器
│   └── /stop                 # 停止调度器
├── /tasks/
│   ├── POST /                # 创建任务
│   ├── GET /                 # 列出所有任务
│   ├── GET /{task_id}        # 获取任务详情
│   ├── DELETE /{task_id}     # 删除任务
│   ├── POST /{task_id}/pause # 暂停任务
│   ├── POST /{task_id}/resume # 恢复任务
│   └── POST /{task_id}/reorder # 调整任务优先级
└── /accounts/
    └── GET /{account_id}/tasks # 获取账户的任务列表
```

## 三、接口详细设计

### 3.1 健康检查

**GET** `/api/v1/health`

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-08T10:30:00",
  "version": "1.0.0"
}
```

### 3.2 调度器管理

#### 3.2.1 获取调度器状态

**GET** `/api/v1/dispatcher/status`

**响应**:
```json
{
  "is_running": true,
  "total_tasks": 5,
  "pending_tasks": 3,
  "running_tasks": 1,
  "paused_tasks": 1,
  "completed_tasks": 0,
  "error_tasks": 0,
  "current_running_task": {
    "task_id": "xxx",
    "account_id": "account_1",
    "started_at": "2026-01-08T10:30:00"
  }
}
```

#### 3.2.2 启动调度器

**POST** `/api/v1/dispatcher/start`

**响应**:
```json
{
  "success": true,
  "message": "调度器已启动"
}
```

#### 3.2.3 停止调度器

**POST** `/api/v1/dispatcher/stop`

**响应**:
```json
{
  "success": true,
  "message": "调度器已停止"
}
```

### 3.3 任务管理

#### 3.3.1 创建任务

**POST** `/api/v1/tasks/`

**请求体**:
```json
{
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
```

**响应**:
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "任务创建成功",
  "task_info": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "account_id": "account_1",
    "account_name": "账号1",
    "status": "pending",
    "next_execution_time": "2026-01-08T11:30:00",
    "created_at": "2026-01-08T10:30:00"
  }
}
```

**错误响应** (账户ID已存在):
```json
{
  "success": false,
  "error": "账户ID 'account_1' 已存在任务 'xxx'，同一账户不能创建多个任务"
}
```

#### 3.3.2 列出所有任务

**GET** `/api/v1/tasks/`

**查询参数**:
- `account_id` (可选): 过滤指定账户的任务
- `status` (可选): 过滤指定状态的任务 (pending/running/paused/completed/error)
- `limit` (可选): 返回数量限制，默认 100
- `offset` (可选): 偏移量，默认 0

**响应**:
```json
{
  "total": 5,
  "tasks": [
    {
      "task_id": "xxx",
      "account_id": "account_1",
      "account_name": "账号1",
      "task_type": "xhs_type",
      "status": "pending",
      "interval": 3600,
      "valid_time_range": [8, 22],
      "task_end_time": "2026-02-08",
      "last_execution_time": "2026-01-08T10:30:00",
      "next_execution_time": "2026-01-08T11:30:00",
      "created_at": "2026-01-08T09:00:00",
      "updated_at": "2026-01-08T10:30:00"
    }
  ]
}
```

#### 3.3.3 获取任务详情

**GET** `/api/v1/tasks/{task_id}`

**响应**:
```json
{
  "task_id": "xxx",
  "account_id": "account_1",
  "account_name": "账号1",
  "task_type": "xhs_type",
  "status": "pending",
  "interval": 3600,
  "valid_time_range": [8, 22],
  "task_end_time": "2026-02-08",
  "last_execution_time": "2026-01-08T10:30:00",
  "next_execution_time": "2026-01-08T11:30:00",
  "created_at": "2026-01-08T09:00:00",
  "updated_at": "2026-01-08T10:30:00",
  "round_num": 5,
  "kwargs": {
    "user_query": "开始运营",
    "user_topic": "科技",
    ...
  }
}
```

**错误响应** (任务不存在):
```json
{
  "success": false,
  "error": "任务不存在: xxx"
}
```

#### 3.3.4 删除任务

**DELETE** `/api/v1/tasks/{task_id}`

**响应**:
```json
{
  "success": true,
  "message": "任务删除成功"
}
```

#### 3.3.5 暂停任务

**POST** `/api/v1/tasks/{task_id}/pause`

**响应**:
```json
{
  "success": true,
  "message": "任务暂停成功",
  "task_id": "xxx",
  "status": "paused"
}
```

#### 3.3.6 恢复任务

**POST** `/api/v1/tasks/{task_id}/resume`

**响应**:
```json
{
  "success": true,
  "message": "任务恢复成功",
  "task_id": "xxx",
  "status": "pending",
  "next_execution_time": "2026-01-08T11:30:00"
}
```

#### 3.3.7 调整任务优先级

**POST** `/api/v1/tasks/{task_id}/reorder`

**请求体**:
```json
{
  "priority_offset": -1800
}
```

**说明**:
- `priority_offset`: 优先级偏移量（秒）
  - 正数：延后执行（如 3600 表示延后1小时）
  - 负数：提前执行（如 -1800 表示提前30分钟）

**响应**:
```json
{
  "success": true,
  "message": "任务优先级调整成功",
  "task_id": "xxx",
  "new_next_execution_time": "2026-01-08T11:00:00"
}
```

**错误响应** (任务正在运行):
```json
{
  "success": false,
  "error": "任务正在运行，无法调整优先级"
}
```

### 3.4 账户管理

#### 3.4.1 获取账户的任务列表

**GET** `/api/v1/accounts/{account_id}/tasks`

**响应**:
```json
{
  "account_id": "account_1",
  "total": 2,
  "tasks": [
    {
      "task_id": "xxx",
      "status": "pending",
      "next_execution_time": "2026-01-08T11:30:00",
      ...
    }
  ]
}
```

## 四、数据模型设计

### 4.1 请求模型 (Pydantic)

```python
# 创建任务请求
class TaskCreateRequest(BaseModel):
    sys_type: str
    task_type: str = "xhs_type"
    xhs_account_id: str
    xhs_account_name: str
    user_query: Optional[str] = None
    user_topic: Optional[str] = None
    user_style: Optional[str] = None
    user_target_audience: Optional[str] = None
    task_end_time: Optional[str] = None  # ISO date format
    interval: Optional[int] = 3600
    valid_time_range: Optional[List[int]] = [8, 22]

# 调整优先级请求
class TaskReorderRequest(BaseModel):
    priority_offset: int  # 秒数

# 任务查询参数
class TaskQueryParams(BaseModel):
    account_id: Optional[str] = None
    status: Optional[str] = None
    limit: int = 100
    offset: int = 0
```

### 4.2 响应模型 (Pydantic)

```python
# 标准响应
class APIResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Any] = None

# 任务信息响应
class TaskInfoResponse(BaseModel):
    task_id: str
    account_id: str
    account_name: str
    task_type: str
    status: str
    interval: int
    valid_time_range: List[int]
    task_end_time: str
    last_execution_time: Optional[str] = None
    next_execution_time: Optional[str] = None
    created_at: str
    updated_at: str
    round_num: Optional[int] = None

# 调度器状态响应
class DispatcherStatusResponse(BaseModel):
    is_running: bool
    total_tasks: int
    pending_tasks: int
    running_tasks: int
    paused_tasks: int
    completed_tasks: int
    error_tasks: int
    current_running_task: Optional[Dict] = None
```

## 五、文件结构

```
app/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── dependencies.py      # 依赖注入（获取 dispatcher 实例）
│   ├── models.py            # Pydantic 数据模型
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py        # 健康检查路由
│   │   ├── dispatcher.py    # 调度器管理路由
│   │   ├── tasks.py          # 任务管理路由
│   │   └── accounts.py       # 账户管理路由
│   └── exceptions.py        # 自定义异常处理
└── manager/
    └── task_dispatcher.py   # 现有调度器
```

## 六、实现要点

### 6.1 依赖注入

使用 FastAPI 的依赖注入系统，确保整个应用共享同一个 TaskDispatcher 实例：

```python
# dependencies.py
from app.manager.task_dispatcher import TaskDispatcher

_dispatcher_instance: Optional[TaskDispatcher] = None

def get_dispatcher() -> TaskDispatcher:
    global _dispatcher_instance
    if _dispatcher_instance is None:
        _dispatcher_instance = TaskDispatcher()
    return _dispatcher_instance
```

### 6.2 异常处理

统一异常处理，返回标准格式的错误响应：

```python
# exceptions.py
from fastapi import HTTPException

class TaskNotFoundError(HTTPException):
    def __init__(self, task_id: str):
        super().__init__(
            status_code=404,
            detail=f"任务不存在: {task_id}"
        )

class AccountExistsError(HTTPException):
    def __init__(self, account_id: str, existing_task_id: str):
        super().__init__(
            status_code=400,
            detail=f"账户ID '{account_id}' 已存在任务 '{existing_task_id}'"
        )
```

### 6.3 异步支持

所有涉及 TaskDispatcher 的操作都应该是异步的：

```python
@router.post("/tasks/")
async def create_task(
    request: TaskCreateRequest,
    dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    task_id = await dispatcher.add_task(**request.dict())
    return {"success": True, "task_id": task_id}
```

### 6.4 数据转换

将 TaskInfo 转换为响应模型：

```python
def task_info_to_response(task_info: TaskInfo) -> TaskInfoResponse:
    return TaskInfoResponse(
        task_id=task_info.task_id,
        account_id=task_info.account_id,
        account_name=task_info.account_name,
        task_type=task_info.task_type,
        status=task_info.status.value,
        interval=task_info.interval,
        valid_time_range=task_info.valid_time_range,
        task_end_time=task_info.task_end_time.isoformat(),
        last_execution_time=task_info.last_execution_time.isoformat() if task_info.last_execution_time else None,
        next_execution_time=task_info.next_execution_time.isoformat() if task_info.next_execution_time else None,
        created_at=task_info.created_at.isoformat(),
        updated_at=task_info.updated_at.isoformat(),
        round_num=task_info.task_manager.round_num
    )
```

## 七、启动和配置

### 7.1 启动脚本

```python
# app/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import health, dispatcher, tasks, accounts

app = FastAPI(
    title="任务调度器 API",
    description="任务调度器 Web API 接口",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix="/api/v1", tags=["健康检查"])
app.include_router(dispatcher.router, prefix="/api/v1/dispatcher", tags=["调度器管理"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["任务管理"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["账户管理"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 7.2 运行方式

```bash
# 方式1: 直接运行
python -m app.api.main

# 方式2: 使用 uvicorn
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

# 方式3: 使用 gunicorn (生产环境)
gunicorn app.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 八、API 文档

### 8.1 自动文档

FastAPI 自动生成交互式 API 文档：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### 8.2 文档增强

可以通过添加描述和示例来增强文档：

```python
@router.post(
    "/tasks/",
    response_model=TaskCreateResponse,
    summary="创建新任务",
    description="创建一个新的任务，如果账户ID已存在任务则返回错误",
    responses={
        200: {"description": "任务创建成功"},
        400: {"description": "账户ID已存在或参数错误"},
    }
)
async def create_task(...):
    ...
```

## 九、安全考虑

### 9.1 认证授权（可选）

如果需要，可以添加认证：

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@router.post("/tasks/")
async def create_task(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    ...
):
    # 验证 token
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="未授权")
    ...
```

### 9.2 输入验证

Pydantic 自动进行数据验证，确保：
- 必填字段存在
- 数据类型正确
- 数据格式符合要求

### 9.3 错误处理

统一错误响应格式，不暴露内部错误信息：

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "内部服务器错误"}
    )
```

## 十、测试建议

### 10.1 单元测试

使用 `pytest` 和 `httpx` 进行测试：

```python
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_create_task():
    response = client.post("/api/v1/tasks/", json={
        "sys_type": "mac_intel",
        "xhs_account_id": "test_account",
        ...
    })
    assert response.status_code == 200
    assert response.json()["success"] == True
```

### 10.2 集成测试

测试完整的任务生命周期：

```python
def test_task_lifecycle():
    # 1. 创建任务
    create_response = client.post("/api/v1/tasks/", json={...})
    task_id = create_response.json()["task_id"]
    
    # 2. 获取任务
    get_response = client.get(f"/api/v1/tasks/{task_id}")
    assert get_response.status_code == 200
    
    # 3. 暂停任务
    pause_response = client.post(f"/api/v1/tasks/{task_id}/pause")
    assert pause_response.status_code == 200
    
    # 4. 恢复任务
    resume_response = client.post(f"/api/v1/tasks/{task_id}/resume")
    assert resume_response.status_code == 200
    
    # 5. 删除任务
    delete_response = client.delete(f"/api/v1/tasks/{task_id}")
    assert delete_response.status_code == 200
```

## 十一、性能优化

### 11.1 异步操作

所有 I/O 操作使用异步，提高并发性能。

### 11.2 缓存（可选）

对于频繁查询的任务列表，可以考虑添加缓存：

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=100)
def get_cached_task_list(account_id: str, cache_key: str):
    # cache_key 可以是时间戳，实现 TTL
    ...
```

### 11.3 分页

任务列表接口支持分页，避免一次性返回大量数据。

## 十二、部署建议

### 12.1 环境变量配置

```bash
# .env
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
LOG_LEVEL=INFO
```

### 12.2 Docker 部署（可选）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 十三、总结

### 13.1 优势

✅ **自动文档**: FastAPI 自动生成交互式 API 文档
✅ **类型安全**: Pydantic 提供完整的数据验证
✅ **异步支持**: 原生支持 async/await，性能优秀
✅ **易于扩展**: 模块化设计，易于添加新功能
✅ **标准 RESTful**: 符合 REST 设计规范

### 13.2 实现步骤

1. **第一阶段**: 基础接口（健康检查、任务 CRUD）
2. **第二阶段**: 调度器管理接口
3. **第三阶段**: 高级功能（优先级调整、账户管理）
4. **第四阶段**: 测试和优化

### 13.3 注意事项

- 确保 TaskDispatcher 实例在整个应用生命周期中唯一
- 所有异步操作正确处理异常
- 保持 API 响应格式统一
- 生产环境需要添加认证和限流

## 十四、示例请求

### 14.1 完整工作流示例

```bash
# 1. 健康检查
curl http://localhost:8000/api/v1/health

# 2. 创建任务
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "sys_type": "mac_intel",
    "xhs_account_id": "account_1",
    "xhs_account_name": "账号1",
    "user_query": "开始运营",
    "interval": 3600,
    "valid_time_range": [8, 22]
  }'

# 3. 获取任务列表
curl http://localhost:8000/api/v1/tasks/

# 4. 暂停任务
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/pause

# 5. 恢复任务
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/resume

# 6. 启动调度器
curl -X POST http://localhost:8000/api/v1/dispatcher/start
```


