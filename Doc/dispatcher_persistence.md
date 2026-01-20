# 调度器持久化功能说明

## 功能概述

TaskDispatcher 现在支持完整的持久化功能，可以保存和恢复所有任务状态，确保系统重启后任务能够继续执行。

## 持久化目录结构

```
app/manager/
└── dispatcher/
    └── dispatch_config.json  # 调度器配置文件
```

## 配置文件格式

`dispatch_config.json` 文件包含以下信息：

```json
{
  "version": "1.0",
  "saved_at": "2026-01-08T00:36:37.121980",
  "tasks": [
    {
      "task_id": "任务ID",
      "account_id": "账户ID",
      "account_name": "账户名称",
      "task_type": "任务类型",
      "status": "任务状态（pending/running/paused/completed/error）",
      "interval": 3600,
      "valid_time_range": [8, 22],
      "task_end_time": "2026-02-08",
      "last_execution_time": "2026-01-08T10:30:00",
      "next_execution_time": "2026-01-08T11:30:00",
      "created_at": "2026-01-08T00:00:00",
      "updated_at": "2026-01-08T10:30:00",
      "kwargs": {
        "task_type": "xhs_type",
        "xhs_account_id": "account_1",
        "xhs_account_name": "账号1",
        "user_query": "查询内容",
        ...
      },
      "sys_type": "mac_intel"
    }
  ],
  "account_tasks": {
    "account_1": ["task_id_1"],
    "account_2": ["task_id_2"]
  }
}
```

## 自动保存时机

调度器会在以下操作后自动保存状态：

1. **添加任务** (`add_task()`)
2. **删除任务** (`remove_task()`)
3. **暂停任务** (`pause_task()`)
4. **恢复任务** (`resume_task()`)
5. **调整优先级** (`reorder_task()`)
6. **任务执行完成** (调度器主循环中)
7. **任务执行异常** (调度器主循环中)
8. **停止调度器** (`stop()`)

## 自动加载时机

调度器在初始化时（`__init__()`）会自动加载历史任务：

1. 检查 `dispatch_config.json` 是否存在
2. 如果存在，读取配置文件
3. 根据保存的参数重新创建 `TaskManager` 实例
4. 恢复所有任务信息（状态、执行时间等）
5. 重建账户任务映射

## 使用示例

### 基本使用（自动持久化）

```python
from app.manager.task_dispatcher import TaskDispatcher
from app.data.constants import SYS_TYPE, DEFAULT_TASK_TYPE
import datetime

# 创建调度器（会自动加载历史任务）
dispatcher = TaskDispatcher()

# 添加任务（会自动保存）
task_id = await dispatcher.add_task(
    sys_type=SYS_TYPE.MAC_INTEL.value,
    task_type=DEFAULT_TASK_TYPE.XHS_TYPE,
    xhs_account_id='account_1',
    xhs_account_name='账号1',
    user_query='开始运营',
    task_end_time=datetime.date.today() + datetime.timedelta(days=30),
    interval=3600,
    valid_time_rage=[8, 22]
)

# 启动调度器
await dispatcher.start()

# 所有操作都会自动保存
dispatcher.pause_task(task_id)
dispatcher.resume_task(task_id)

# 停止调度器（会自动保存最终状态）
await dispatcher.stop()
```

### 自定义持久化目录

```python
# 使用自定义目录
dispatcher = TaskDispatcher(dispatcher_dir="./custom_dispatcher/")
```

## 持久化内容

### 保存的信息

1. **任务基本信息**：
   - task_id, account_id, account_name, task_type
   - status, interval, valid_time_range, task_end_time

2. **执行时间信息**：
   - last_execution_time（上次执行时间）
   - next_execution_time（下次执行时间）
   - created_at, updated_at

3. **任务创建参数**：
   - 完整的 kwargs（用于恢复 TaskManager）
   - sys_type（系统类型）

4. **账户任务映射**：
   - account_tasks（账户ID到任务ID列表的映射）

### 不保存的信息

- `task_manager` 对象（不能直接序列化，通过参数重新创建）
- `running_task`（运行时状态，不需要持久化）
- `scheduler_task`（运行时状态，不需要持久化）
- `execution_lock`（运行时状态，不需要持久化）

## 恢复机制

### TaskManager 恢复

由于 `TaskManager` 对象不能直接序列化，恢复时：

1. 从配置文件中读取 `kwargs` 和 `sys_type`
2. 使用 `TaskManager(sys_type=sys_type, **kwargs)` 重新创建实例
3. `kwargs` 中包含 `task_id`，确保 TaskManager 能够从 context 恢复历史状态

### 状态恢复

1. 恢复任务状态（PENDING, PAUSED, COMPLETED 等）
2. 恢复执行时间（last_execution_time, next_execution_time）
3. 恢复元数据（created_at, updated_at）
4. 重建账户任务映射

## 错误处理

### 保存失败

- 如果保存失败，会记录错误日志，但不影响调度器运行
- 使用 `logger.error()` 记录详细错误信息

### 加载失败

- 如果配置文件不存在，使用空状态（新调度器）
- 如果配置文件损坏，记录错误日志，使用空状态
- 如果某个任务恢复失败，跳过该任务，继续恢复其他任务

## 注意事项

1. **文件权限**：确保调度器有读写 `dispatcher/` 目录的权限
2. **并发安全**：持久化操作在关键操作后执行，确保状态一致性
3. **性能考虑**：频繁保存可能影响性能，但保证了数据安全
4. **备份建议**：定期备份 `dispatch_config.json` 文件

## 文件位置

- **默认目录**：`app/manager/dispatcher/`
- **配置文件**：`app/manager/dispatcher/dispatch_config.json`
- **可自定义**：通过 `TaskDispatcher(dispatcher_dir="...")` 指定

## 测试

运行持久化测试：

```bash
python3 -m app.manager.test_persistence
```

测试内容包括：
- 持久化文件结构验证
- 日期时间序列化验证
- 配置文件读写验证

## 总结

✅ **持久化功能完整实现**：
- 自动保存任务状态
- 自动加载历史任务
- 支持系统重启后恢复
- 错误处理完善

✅ **使用简单**：
- 无需手动调用保存/加载方法
- 所有操作自动持久化
- 初始化时自动恢复

✅ **数据安全**：
- 关键操作后立即保存
- 支持异常恢复
- 详细的错误日志

