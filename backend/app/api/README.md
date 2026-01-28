# 任务调度器 Web API

基于 FastAPI 的 RESTful API 接口，提供任务调度器的完整管理功能。

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn
```

或者取消注释 `requirements.txt` 中的相关行：
```txt
fastapi>=0.104.0
uvicorn>=0.24.0
```

### 2. 启动服务

```bash
# 方式1: 直接运行
python -m app.api.main

# 方式2: 使用 uvicorn
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

# 方式3: 指定配置文件
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

### 3. 访问 API 文档

启动后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API 端点

### 健康检查
- `GET /api/v1/health` - 健康检查

### 调度器管理
- `GET /api/v1/dispatcher/status` - 获取调度器状态
- `POST /api/v1/dispatcher/start` - 启动调度器
- `POST /api/v1/dispatcher/stop` - 停止调度器

### 任务管理
- `POST /api/v1/tasks/` - 创建任务
- `GET /api/v1/tasks/` - 列出所有任务
- `GET /api/v1/tasks/{task_id}` - 获取任务详情
- `DELETE /api/v1/tasks/{task_id}` - 删除任务
- `POST /api/v1/tasks/{task_id}/pause` - 暂停任务
- `POST /api/v1/tasks/{task_id}/resume` - 恢复任务
- `POST /api/v1/tasks/{task_id}/reorder` - 调整任务优先级

### 账户管理
- `GET /api/v1/accounts/{account_id}/tasks` - 获取账户的任务列表

## 使用示例

### 创建任务

```bash
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
```

### 获取任务列表

```bash
curl http://localhost:8000/api/v1/tasks/
```

### 启动调度器

```bash
curl -X POST http://localhost:8000/api/v1/dispatcher/start
```

## 文件结构

```
app/api/
├── __init__.py
├── main.py              # FastAPI 应用入口
├── models.py            # Pydantic 数据模型
├── dependencies.py      # 依赖注入
├── exceptions.py        # 异常处理
├── utils.py             # 工具函数
├── routers/             # 路由模块
│   ├── __init__.py
│   ├── health.py        # 健康检查
│   ├── dispatcher.py    # 调度器管理
│   ├── tasks.py         # 任务管理
│   └── accounts.py      # 账户管理
└── README.md
```

## 注意事项

1. **单例模式**: TaskDispatcher 使用单例模式，确保整个应用共享同一个实例
2. **持久化**: 调度器状态会自动持久化到 `app/manager/dispatcher/dispatch_config.json`
3. **异步支持**: 所有接口都支持异步操作
4. **错误处理**: 统一的错误响应格式
5. **CORS**: 当前配置允许所有来源，生产环境应限制

## 开发

### 运行测试

```bash
# 使用 pytest 运行测试
pytest app/api/tests/
```

### 代码检查

```bash
# 使用 flake8 检查代码
flake8 app/api/

# 使用 mypy 进行类型检查
mypy app/api/
```

