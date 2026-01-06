# 任务调度器开发方案

## 一、需求分析

### 1.1 核心问题
- **Cookie冲突问题**：任务执行时需要使用cookie文件，由于cookie是共享资源，**所有任务必须串行执行，不能并行**。无论是否同一账户，同一时间只能有一个任务在运行。
- **任务管理需求**：需要统一管理多个任务，支持任务的添加、删除、暂停、恢复
- **用户交互需求**：用户需要能够通过点选操作来控制任务的执行状态，包括调整任务在队列中的顺序

### 1.2 现有机制分析
- `TaskManager` 已经实现了单个任务的执行逻辑
- **优化后**：`TaskManager.run()` 改为单次执行模式，每次调用只执行一次，不再包含循环
- 任务已有内置的暂停/恢复机制（通过 `task_switch` 的 `PAUSE`/`RUNNING` 状态）
- 任务通过 `task_id` 和 `xhs_account_id` 唯一标识
- 每个任务有自己的执行时间配置：`interval`（执行间隔）、`valid_time_range`（有效时间范围）、`task_end_time`（结束时间）

## 二、设计方案

### 2.1 架构设计

```
TaskDispatcher (调度器)
    ├── GlobalLock (全局锁)
    │   └── execution_lock: asyncio.Lock  # 全局执行锁，确保所有任务串行执行
    │
    ├── TimeBasedScheduler (基于时间的调度器)
    │   ├── scheduler_loop: asyncio.Task  # 调度器主循环
    │   └── next_check_time: datetime  # 下次检查时间
    │
    ├── TaskRegistry (任务注册表)
    │   ├── all_tasks: Dict[str, TaskInfo]  # 所有任务信息（task_id -> TaskInfo）
    │   ├── account_tasks: Dict[str, List[str]]  # 账户任务映射（account_id -> [task_id, ...]）
    │   └── running_task: Optional[TaskInfo]  # 当前正在运行的任务
    │
    └── ControlAPI (控制接口)
        ├── add_task()  # 添加任务（含账户ID唯一性校验）
        ├── remove_task()  # 删除任务
        ├── pause_task()  # 暂停任务
        ├── resume_task()  # 恢复任务
        ├── reorder_task()  # 调整任务执行优先级（通过修改next_execution_time）
        └── get_task_status()  # 获取任务状态
```


### 2.2 核心组件

#### 2.2.1 TaskDispatcher（主调度器）
**职责**：
- **基于时间的任务调度**：根据每个任务的执行时间配置，智能调度任务执行
- 使用全局锁确保所有任务串行执行
- 提供任务控制接口
- 维护账户ID唯一性约束

**关键设计**：
- 使用**单个全局锁**（`asyncio.Lock`）确保所有任务串行执行，避免cookie冲突
- **基于时间的调度机制**：每个任务维护 `next_execution_time`，调度器根据时间顺序执行
- 任务可以按照各自的 `interval` 和 `valid_time_range` 交错执行，提高资源利用率
- 在添加任务时校验账户ID唯一性，防止同一账户创建多个任务

**数据结构**：
```python
{
    "execution_lock": asyncio.Lock(),  # 全局执行锁
    "all_tasks": {
        "task_id_1": TaskInfo(...),  # 包含 next_execution_time
        "task_id_2": TaskInfo(...),
        ...
    },
    "account_tasks": {
        "account_id_1": ["task_id_1"],
        "account_id_2": ["task_id_2"],
        ...
    },
    "running_task": TaskInfo or None  # 当前运行的任务
}
```

#### 2.2.3 TaskInfo（任务信息）
**数据结构**：
```python
@dataclass
class TaskInfo:
    task_id: str
    account_id: str
    account_name: str
    task_type: str
    task_manager: TaskManager
    status: TaskStatus  # PENDING, RUNNING, PAUSED, COMPLETED, ERROR
    
    # 时间相关字段
    interval: int  # 执行间隔（秒）
    valid_time_range: List[int]  # 有效时间范围 [start_hour, end_hour]
    task_end_time: datetime.date  # 任务结束时间
    last_execution_time: Optional[datetime]  # 上次执行时间
    next_execution_time: Optional[datetime]  # 下次执行时间
    
    created_at: datetime
    updated_at: datetime
    kwargs: dict  # 任务创建参数
```

#### 2.2.4 TaskStatus（任务状态枚举）
```python
class TaskStatus(Enum):
    PENDING = "pending"      # 等待执行
    RUNNING = "running"       # 正在执行
    PAUSED = "paused"         # 已暂停
    COMPLETED = "completed"   # 已完成
    ERROR = "error"           # 执行错误
```

### 2.3 执行流程

#### 2.3.1 任务添加流程
```
1. 用户调用 add_task() 添加任务
2. 校验账户ID唯一性：
   - 根据任务类型（如 XHS_TYPE）提取账户ID（xhs_account_id）
   - 检查调度器中是否已存在相同任务类型和相同账户ID的任务
   - 如果存在，抛出异常，拒绝创建任务
3. 创建 TaskManager 实例
4. 创建 TaskInfo 对象，初始化时间字段：
   - interval: 从 kwargs 获取
   - valid_time_range: 从 kwargs 获取
   - task_end_time: 从 kwargs 获取
   - last_execution_time: None（首次执行）
   - next_execution_time: 计算得出（如果当前时间在有效范围内，立即执行；否则调整到下一个有效时间段）
5. 更新任务注册表（all_tasks 和 account_tasks）
6. 触发调度器重新计算下次检查时间
```

#### 2.3.2 调度器主循环流程
```
1. 调度器启动后，进入主循环
2. 找到所有 next_execution_time <= now 的任务
3. 按 next_execution_time 排序（时间冲突时按创建时间排序）
4. 如果有待执行任务：
   a. 获取全局执行锁
   b. 取出第一个任务
   c. 标记任务状态为 RUNNING
   d. 设置 running_task 为当前任务
   e. 调用 TaskManager.run_once() 执行任务（单次执行）
   f. 更新 last_execution_time = now
   g. 计算 next_execution_time（考虑 interval 和 valid_time_range）
   h. 如果任务已到期（now >= task_end_time），标记为 COMPLETED
   i. 清理 running_task
   j. 释放全局锁
5. 计算下次检查时间（最近的任务 next_execution_time）
6. 等待到下次检查时间（或最多等待60秒后重新检查）
7. 重复步骤2-6
```

#### 2.3.3 下次执行时间计算规则
```
计算 next_execution_time：
1. 基础时间 = last_execution_time + interval
2. 如果基础时间 < task_end_time：
   a. 检查基础时间是否在 valid_time_range 内
   b. 如果在范围内，next_execution_time = 基础时间
   c. 如果不在范围内，调整到下一个有效时间段的开始：
      - 如果基础时间 < start_hour，调整到当天的 start_hour
      - 如果基础时间 > end_hour，调整到次日的 start_hour
3. 如果基础时间 >= task_end_time，next_execution_time = None（任务已结束）
```

#### 2.3.4 任务暂停/恢复流程
```
暂停：
1. 用户调用 pause_task(task_id)
2. 查找任务对应的 TaskManager
3. 调用 TaskManager.task_pause()
4. 设置 next_execution_time = None（暂停调度）
5. 更新任务状态为 PAUSED

恢复：
1. 用户调用 resume_task(task_id)
2. 查找任务对应的 TaskManager
3. 调用 TaskManager.task_resume()
4. 重新计算 next_execution_time（基于 last_execution_time 或 now）
5. 更新任务状态为 PENDING
6. 触发调度器重新计算下次检查时间
```

#### 2.3.5 任务执行优先级调整流程
```
1. 用户调用 reorder_task(task_id, priority_offset)
   - priority_offset: 优先级偏移量（秒），正数表示延后，负数表示提前
2. 如果任务正在运行，抛出异常（不能调整正在运行的任务）
3. 如果任务已暂停，抛出异常（需要先恢复任务）
4. 调整 next_execution_time = next_execution_time + priority_offset
5. 确保调整后的时间在 valid_time_range 内（如果不在，调整到最近的有效时间）
6. 触发调度器重新计算下次检查时间
```

### 2.4 关键实现细节

#### 2.4.1 全局锁机制
```python
# 使用单个全局锁确保所有任务串行执行
execution_lock = asyncio.Lock()

async def execute_task(task_info: TaskInfo):
    async with execution_lock:
        # 串行执行任务，确保cookie不冲突
        task_info.status = TaskStatus.RUNNING
        should_continue = await task_info.task_manager.run_once()
        
        # 更新执行时间
        task_info.last_execution_time = datetime.datetime.now()
        
        if should_continue:
            # 计算下次执行时间
            task_info.next_execution_time = calculate_next_execution_time(task_info)
        else:
            # 任务已到期
            task_info.next_execution_time = None
            task_info.status = TaskStatus.COMPLETED
```

#### 2.4.1.1 时间调度算法
```python
def calculate_next_execution_time(task_info: TaskInfo) -> Optional[datetime]:
    """
    计算任务的下次执行时间
    
    规则：
    1. 基础时间 = last_execution_time + interval
    2. 如果基础时间不在 valid_time_range 内，调整到下一个有效时间段
    3. 如果超过 task_end_time，返回 None
    """
    if task_info.last_execution_time is None:
        # 首次执行
        now = datetime.datetime.now()
        if is_in_valid_time_range(now, task_info.valid_time_range):
            return now
        else:
            return get_next_valid_time_start(now, task_info.valid_time_range)
    
    # 计算基础时间
    base_time = task_info.last_execution_time + datetime.timedelta(seconds=task_info.interval)
    
    # 检查是否超过结束时间
    if base_time.date() >= task_info.task_end_time:
        return None
    
    # 检查是否在有效时间范围内
    if is_in_valid_time_range(base_time, task_info.valid_time_range):
        return base_time
    else:
        # 调整到下一个有效时间段的开始
        return get_next_valid_time_start(base_time, task_info.valid_time_range)
```

#### 2.4.1.1 账户ID唯一性校验
```python
def _validate_account_uniqueness(self, task_type: str, account_id: str):
    """
    校验账户ID唯一性
    
    规则：
    - 对于同一任务类型（如 XHS_TYPE），每个账户ID只能对应一个任务
    - 如果已存在相同任务类型和相同账户ID的任务，则拒绝创建新任务
    
    Args:
        task_type: 任务类型（如 DEFAULT_TASK_TYPE.XHS_TYPE）
        account_id: 账户ID（如 xhs_account_id）
        
    Raises:
        ValueError: 如果账户ID已存在，包含详细信息
    """
    # 检查该任务类型下是否已存在相同账户ID的任务
    for task_id, task_info in self.all_tasks.items():
        if task_info.task_type == task_type and task_info.account_id == account_id:
            raise ValueError(
                f"账户ID '{account_id}' 已存在任务 '{task_id}'（状态: {task_info.status}），"
                f"同一账户不能创建多个任务。请先删除或完成现有任务。"
            )
```

**校验时机**：
- 在 `add_task()` 方法中，创建 TaskManager 之前进行校验
- 如果校验失败，立即抛出异常，不创建任何资源

#### 2.4.2 任务执行包装
```python
async def run_task_with_error_handling(task_info: TaskInfo) -> bool:
    """
    执行任务并处理异常
    
    Returns:
        bool: 是否应该继续执行（False表示任务已到期）
    """
    try:
        task_info.status = TaskStatus.RUNNING
        should_continue = await task_info.task_manager.run_once()
        
        if should_continue:
            # 任务未到期，可以继续调度
            task_info.status = TaskStatus.PENDING
        else:
            # 任务已到期
            task_info.status = TaskStatus.COMPLETED
            
        return should_continue
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        task_info.status = TaskStatus.ERROR
        # 即使出错，如果任务未到期，仍然可以继续调度
        return datetime.datetime.now().date() < task_info.task_end_time
    finally:
        # 清理工作
        pass
```

#### 2.4.3 任务状态持久化
- 使用 `Task_Manager_Context` 保存任务元数据
- 调度器状态可以保存到独立的配置文件（`dispatcher_state.json`）
- 支持系统重启后恢复任务状态

## 三、接口设计

### 3.1 TaskDispatcher 类接口

```python

class TaskDispatcher:
    def __init__(self):
        """
        初始化调度器
        
        初始化：
        - execution_lock: 全局执行锁
        - task_queue: 任务队列
        - all_tasks: 任务注册表
        - account_tasks: 账户任务映射
        - running_task: 当前运行的任务
        """
        pass
    
    async def add_task(self, sys_type: str, **kwargs) -> str:
        """
        添加新任务
        
        Args:
            sys_type: 操作系统类型
            **kwargs: TaskManager 初始化参数
                - task_type: 任务类型（如 DEFAULT_TASK_TYPE.XHS_TYPE）
                - xhs_account_id: 小红书账户ID（必填，用于XHS_TYPE）
                - ... 其他 TaskManager 参数
            
        Returns:
            task_id: 新创建的任务ID
            
        Raises:
            ValueError: 如果账户ID已存在（同一任务类型下账户ID必须唯一）
        """
        pass
    
    async def remove_task(self, task_id: str) -> bool:
        """
        删除任务（如果任务正在运行，先暂停再删除）
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否删除成功
        """
        pass
    
    def pause_task(self, task_id: str) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否暂停成功
        """
        pass
    
    def resume_task(self, task_id: str) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否恢复成功
        """
        pass
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            TaskInfo: 任务信息，如果不存在返回 None
        """
        pass
    
    def list_tasks(self, account_id: Optional[str] = None) -> List[TaskInfo]:
        """
        列出所有任务
        
        Args:
            account_id: 可选，如果指定则只返回该账户的任务
            
        Returns:
            List[TaskInfo]: 任务列表（按 next_execution_time 排序）
        """
        pass
    
    def reorder_task(self, task_id: str, priority_offset: int) -> bool:
        """
        调整任务的执行优先级（通过修改 next_execution_time）
        
        Args:
            task_id: 任务ID
            priority_offset: 优先级偏移量（秒）
                - 正数：延后执行（如 3600 表示延后1小时）
                - 负数：提前执行（如 -1800 表示提前30分钟）
            
        Returns:
            bool: 是否调整成功
            
        Raises:
            ValueError: 如果任务不存在、正在运行、已暂停或已结束
        """
        pass
    
    async def start(self):
        """启动调度器（开始执行任务队列）"""
        pass
    
    async def stop(self):
        """停止调度器（等待当前任务完成，不再执行新任务）"""
        pass
```

### 3.2 用户交互接口（可选）

如果需要提供Web API或CLI接口：

```python
# Web API 示例（使用 FastAPI）
@app.post("/tasks")
async def create_task(request: TaskCreateRequest):
    task_id = await dispatcher.add_task(**request.dict())
    return {"task_id": task_id}

@app.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str):
    success = dispatcher.pause_task(task_id)
    return {"success": success}

@app.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    success = dispatcher.resume_task(task_id)
    return {"success": success}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task_info = dispatcher.get_task_status(task_id)
    return task_info
```

## 四、实现计划

### 4.1 第一阶段：核心调度器
1. 实现 `TaskDispatcher` 基础类
2. 实现全局任务队列管理
3. 实现全局锁机制（确保所有任务串行执行）
4. 实现任务添加和执行逻辑
5. 实现账户ID唯一性校验

### 4.2 第二阶段：任务控制
1. 实现任务暂停/恢复功能
2. 实现任务删除功能
3. 实现任务状态查询
4. 实现任务队列顺序调整功能（reorder_task）

### 4.3 第三阶段：持久化和恢复
1. 实现调度器状态持久化
2. 实现系统重启后任务恢复
3. 实现任务状态监控和日志

### 4.4 第四阶段：用户接口（可选）
1. 实现CLI接口
2. 实现Web API接口（可选）
3. 实现Web UI（可选，暂不设计）

## 五、技术要点

### 5.1 异步编程
- 使用 `asyncio` 实现异步任务调度
- 使用 `asyncio.Lock` 实现账户级别的串行控制
- 使用 `asyncio.create_task` 创建任务执行协程

### 5.2 错误处理
- 任务执行异常不应影响其他任务
- 记录详细的错误日志
- 提供任务重试机制（可选）

### 5.3 资源管理
- 及时清理已完成的任务
- 管理 TaskManager 实例的生命周期
- 避免内存泄漏

### 5.4 并发控制
- **所有任务必须串行执行**：由于cookie是共享资源，无论是否同一账户，同一时间只能有一个任务运行
- 使用全局锁机制确保任务串行执行
- 使用锁机制确保线程安全

## 六、文件结构

```
app/manager/
├── task_manager.py          # 现有任务管理器
├── task_context.py          # 现有任务上下文
├── task_dispatcher.py       # 新增：任务调度器
├── task_info.py             # 新增：任务信息数据结构
└── dispatcher_state.py      # 新增：调度器状态管理（可选）
```

## 七、使用示例

```python
# 初始化调度器
dispatcher = TaskDispatcher()

# 添加任务
task_id_1 = await dispatcher.add_task(
    sys_type=SYS_TYPE.MAC_INTEL.value,
    task_type=DEFAULT_TASK_TYPE.XHS_TYPE,
    xhs_account_id='account_1',
    xhs_account_name='账号1',
    user_query='开始运营',
    # ... 其他参数
)

# 尝试添加同一账户的第二个任务（会抛出异常）
try:
    task_id_2 = await dispatcher.add_task(
        sys_type=SYS_TYPE.MAC_INTEL.value,
        task_type=DEFAULT_TASK_TYPE.XHS_TYPE,
        xhs_account_id='account_1',  # 与 task_id_1 相同，会抛出 ValueError
        xhs_account_name='账号1',
        user_query='继续运营',
    )
except ValueError as e:
    print(f"无法创建任务: {e}")  # 账户ID已存在

# 添加不同账户的任务（可以创建，但会串行执行）
task_id_3 = await dispatcher.add_task(
    sys_type=SYS_TYPE.MAC_INTEL.value,
    task_type=DEFAULT_TASK_TYPE.XHS_TYPE,
    xhs_account_id='account_2',  # 不同账户，可以创建
    xhs_account_name='账号2',
    user_query='开始运营',
)

# 启动调度器
await dispatcher.start()

# 用户操作：暂停任务
dispatcher.pause_task(task_id_1)

# 用户操作：恢复任务
dispatcher.resume_task(task_id_1)

# 用户操作：调整任务执行优先级
dispatcher.reorder_task(task_id_3, priority_offset=-3600)  # 提前1小时执行

# 查看任务状态
status = dispatcher.get_task_status(task_id_1)
print(f"任务状态: {status.status}")
print(f"下次执行时间: {status.next_execution_time}")

# 列出所有任务（按下次执行时间排序）
all_tasks = dispatcher.list_tasks()
for task in all_tasks:
    print(f"任务 {task.task_id} ({task.account_id}) - 状态: {task.status}, 下次执行: {task.next_execution_time}")

# 停止调度器
await dispatcher.stop()
```

## 八、注意事项

1. **任务单次执行**：`TaskManager.run_once()` 每次只执行一次，不包含循环，调度器负责管理任务的生命周期
2. **时间调度精度**：调度器检查间隔建议为1-60秒，平衡响应速度和系统负载
3. **异常处理**：任务执行异常不应影响调度器的正常运行，错误任务可以继续调度或标记为ERROR
4. **资源清理**：任务完成后（status=COMPLETED）应及时清理相关资源
5. **状态一致性**：确保任务状态在调度器和 TaskManager 之间保持一致
6. **时间冲突处理**：如果多个任务的 next_execution_time 相同，按创建时间顺序执行
7. **暂停任务处理**：暂停的任务 next_execution_time 设为 None，恢复时重新计算

## 九、扩展性考虑

1. **优先级调度**：可以为任务添加优先级，高优先级任务优先执行
2. **任务依赖**：支持任务之间的依赖关系
3. **资源限制**：支持限制同时运行的任务数量
4. **任务重试**：支持失败任务的重试机制
5. **监控告警**：集成监控和告警系统

