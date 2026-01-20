# 服务启动脚本

## 快速开始

### 基本启动

```bash
# 使用默认配置启动（0.0.0.0:8000）
python service/start_api.py

# 或者直接运行（如果已添加执行权限）
./service/start_api.py
```

### 开发模式（自动重载）

```bash
python service/start_api.py --reload
```

### 生产模式（多进程）

```bash
python service/start_api.py --workers 4
```

## 命令行参数

| 参数 | 说明 | 默认值 | 环境变量 |
|------|------|--------|----------|
| `--host` | 绑定主机地址 | `0.0.0.0` | `API_HOST` |
| `--port` | 绑定端口 | `8000` | `API_PORT` |
| `--reload` | 开发模式（自动重载） | `False` | `API_RELOAD` |
| `--workers` | 工作进程数 | `1` | `API_WORKERS` |
| `--log-level` | 日志级别 | `info` | `API_LOG_LEVEL` |
| `--access-log` | 启用访问日志 | `False` | `API_ACCESS_LOG` |
| `--app-dir` | 应用模块路径 | `app.api.main:app` | - |

## 使用示例

### 1. 开发环境

```bash
# 开发模式，自动重载，调试日志
python service/start_api.py --reload --log-level debug
```

### 2. 测试环境

```bash
# 单进程，详细日志
python service/start_api.py --log-level debug --access-log
```

### 3. 生产环境

```bash
# 多进程，生产日志级别
python service/start_api.py --workers 4 --log-level info --access-log
```

### 4. 自定义端口

```bash
# 使用 8080 端口
python service/start_api.py --port 8080
```

### 5. 仅本地访问

```bash
# 仅绑定到本地
python service/start_api.py --host 127.0.0.1
```

## 环境变量配置

可以通过环境变量配置，无需修改命令行：

```bash
# 设置环境变量
export API_HOST=0.0.0.0
export API_PORT=8000
export API_RELOAD=false
export API_WORKERS=4
export API_LOG_LEVEL=info
export API_ACCESS_LOG=true

# 启动服务
python service/start_api.py
```

## 使用 systemd 管理服务（Linux）

创建 systemd 服务文件 `/etc/systemd/system/task-scheduler-api.service`:

```ini
[Unit]
Description=任务调度器 API 服务
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/AiMediaOps
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python service/start_api.py --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl start task-scheduler-api
sudo systemctl enable task-scheduler-api
sudo systemctl status task-scheduler-api
```

## 使用 supervisor 管理服务

创建 supervisor 配置文件 `/etc/supervisor/conf.d/task-scheduler-api.conf`:

```ini
[program:task-scheduler-api]
command=/path/to/venv/bin/python service/start_api.py --workers 4
directory=/path/to/AiMediaOps
user=your_user
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/task-scheduler-api.log
```

启动服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start task-scheduler-api
```

## 注意事项

1. **开发模式** (`--reload`): 仅用于开发，不要在生产环境使用
2. **多进程模式** (`--workers > 1`): 生产环境推荐，但需要确保代码是线程安全的
3. **日志级别**: 生产环境建议使用 `info`，避免过多日志影响性能
4. **访问日志**: 生产环境建议启用，便于监控和排查问题
