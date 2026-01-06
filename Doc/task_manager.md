# TaskManager 优化方案

## 一、优化目标

### 1.1 问题分析

**当前问题**：
- `TaskManager.run()` 方法包含 `while` 循环，会一直运行直到 `task_end_time`
- 任务自己管理生命周期，导致长时间占用资源
- 如果任务周期很长（如30天），其他任务需要等待很久才能执行
- 无法实现任务的交错执行，资源利用率低

**优化目标**：
- 将任务执行改为**单次执行模式**，每次调用只执行一次
- 由调度器（TaskDispatcher）统一管理任务的生命周期和调度
- 实现任务的交错执行，提高资源利用率

## 二、设计方案

### 2.1 核心变更

#### 2.1.1 方法重命名和改造

**原方法**：
```python
async def run(self):
    while datetime.date.today() < self.task_end_time:
        # 检查暂停状态
        # 检查时间范围
        # 执行一次任务
        time.sleep(self.interval)
```

**优化后**：
```python
async def run_once(self) -> bool:
    """
    执行一次任务（单次执行，不包含循环）
    
    每次调用只执行一次任务，然后返回。调度器负责管理任务的生命周期
    和下次执行时间的计算。
    
    Returns:
        bool: 是否应该继续执行
            - True: 任务未到期，可以继续调度
            - False: 任务已到期（now >= task_end_time），不应再执行
    """
    pass
```

### 2.2 详细实现

#### 2.2.1 run_once() 方法实现

```python
async def run_once(self) -> bool:
    """
    执行一次任务
    
    执行流程：
    1. 检查任务是否已到期
    2. 检查任务是否暂停
    3. 检查是否在有效时间范围内
    4. 执行任务（部署cookie、运行agent、收尾）
    5. 更新 round_num
    6. 返回是否应该继续执行
    """
    # 1. 检查任务是否已到期
    if datetime.date.today() >= self.task_end_time:
        logger.info(f"任务 {self.task_id} 已到期（结束时间: {self.task_end_time}），不再执行")
        return False
    
    # 2. 检查任务是否是暂停状态
    if self.task_switch.get('state') == 'PAUSE':
        logger.debug(f"任务 {self.task_id} 第 {self.round_num} 轮次暂停，跳过本次执行")
        return True  # 返回True表示任务未到期，但本次因暂停未执行
    
    # 3. 检查任务是否在执行时间区间内
    if not self._check_time_valid():
        logger.debug(f"任务 {self.task_id} 第 {self.round_num} 轮次未执行，不在执行时间范围内")
        return True  # 返回True表示任务未到期，但本次因时间范围未执行
    
    # 4. 执行任务
    logger.info(f"任务 {self.task_id} 第 {self.round_num} 轮次开始执行")
    
    try:
        # 4.1 检查mcp服务是否正常运行
        self._mcp_service_check()
        
        # 4.2 将用户专属cookies.json文件复制到MCP服务目录
        user_cookies_file = os.path.join(
            get_user_cookies_path(self.xhs_account_id), 
            "cookies.json"
        )
        logger.debug(f"用户专属cookie地址: {user_cookies_file}")
        
        try:
            # 尝试部署账号cookies
            self._dispatch_cookies(
                source_path=user_cookies_file,
                destination_path=COOKIE_TARGET_PATH
            )
        except RuntimeError as e:
            logger.warning(
                f"无法找到该账户cookies储备，删除当前cookies，准备重新登陆，错误: {e}"
            )
            self._clear_cookies()
        
        # 4.3 运行agent任务
        try:
            await self.agent.run()
        except Exception as e:
            logger.warning(f"agent任务执行失败，错误：{e}")
            # 即使agent执行失败，也继续执行收尾工作
        
        # 4.4 任务执行完成后，进行收尾工作
        try:
            self._close_task()
        except Exception as e:
            logger.error(f"任务收尾工作失败: {e}")
        
        # 4.5 更新执行轮次
        self.round_num += 1
        
        # 4.6 保存 round_num 到 context（可选，用于持久化）
        # self.context.save({'round_num': self.round_num})
        
        logger.info(f"任务 {self.task_id} 第 {self.round_num-1} 轮次执行完成")
        
        return True  # 返回True表示任务未到期，可以继续调度
        
    except Exception as e:
        logger.error(f"任务 {self.task_id} 执行过程中发生异常: {e}", exc_info=True)
        # 即使发生异常，如果任务未到期，仍然可以继续调度
        return datetime.date.today() < self.task_end_time
```

### 2.3 关键变更点

#### 2.3.1 移除循环逻辑
- **移除**：`while datetime.date.today() < self.task_end_time` 循环
- **移除**：`time.sleep(self.interval)` 等待逻辑
- **原因**：循环和等待逻辑由调度器统一管理

#### 2.3.2 返回值设计
- **返回类型**：`bool`
- **返回 True**：任务未到期，调度器可以继续调度
- **返回 False**：任务已到期，调度器不应再调度此任务

#### 2.3.3 状态检查逻辑
- **任务到期检查**：在方法开始时检查，如果已到期直接返回 False
- **暂停状态检查**：如果暂停，返回 True（任务未到期，但本次不执行）
- **时间范围检查**：如果不在有效时间范围内，返回 True（任务未到期，但本次不执行）

**注意**：暂停和时间范围检查返回 True 的原因：
- 这些是临时状态，任务本身未到期
- 调度器会根据情况重新调度（恢复后或进入有效时间范围后）

#### 2.3.4 round_num 管理
- **自增时机**：在任务成功执行后自增
- **持久化**：可选，可以保存到 `Task_Manager_Context` 中

### 2.4 与调度器的协作

#### 2.4.1 调度器调用流程
```
调度器主循环：
1. 找到 next_execution_time <= now 的任务
2. 获取全局锁
3. 调用 task_manager.run_once()
4. 根据返回值：
   - True: 计算 next_execution_time，继续调度
   - False: 标记任务为 COMPLETED，不再调度
5. 释放全局锁
```

#### 2.4.2 时间管理职责划分
- **TaskManager**：
  - 检查任务是否到期（`task_end_time`）
  - 检查是否在有效时间范围内（`valid_time_range`）
  - 不管理执行间隔（`interval`）
  
- **TaskDispatcher**：
  - 计算下次执行时间（基于 `interval` 和 `valid_time_range`）
  - 管理任务的调度时机
  - 跟踪 `last_execution_time` 和 `next_execution_time`

## 三、代码变更清单

### 3.1 需要修改的方法

1. **`run()` → `run_once()`**
   - 移除 `while` 循环
   - 移除 `time.sleep(self.interval)`
   - 添加返回值 `bool`
   - 在方法开始时检查任务是否到期

2. **可选优化**：
   - 将 `round_num` 的更新保存到 `context` 中，实现持久化

### 3.2 保持不变的部分

1. **暂停/恢复机制**：
   - `task_pause()` 和 `task_resume()` 方法保持不变
   - `task_switch` 机制保持不变

2. **其他方法**：
   - `_check_time_valid()`：保持不变
   - `_dispatch_cookies()`：保持不变
   - `_close_task()`：保持不变
   - `_mcp_service_check()`：保持不变

## 四、迁移注意事项

### 4.1 向后兼容性

**建议**：如果代码中有直接调用 `run()` 的地方，可以保留 `run()` 方法作为兼容层：

```python
async def run(self):
    """
    兼容方法：循环调用 run_once() 直到任务到期
    
    注意：此方法仅用于向后兼容，新代码应使用调度器调用 run_once()
    """
    while True:
        should_continue = await self.run_once()
        if not should_continue:
            break
        await asyncio.sleep(self.interval)
```

**或者**：直接移除 `run()` 方法，强制使用调度器。

### 4.2 测试要点

1. **单次执行测试**：
   - 验证 `run_once()` 每次只执行一次
   - 验证返回值正确（到期返回 False，未到期返回 True）

2. **状态检查测试**：
   - 验证任务到期时返回 False
   - 验证暂停时返回 True
   - 验证时间范围外时返回 True

3. **异常处理测试**：
   - 验证执行异常时不影响返回值逻辑
   - 验证异常日志记录正确

## 五、优势总结

### 5.1 职责分离
- **TaskManager**：专注于单次任务执行
- **TaskDispatcher**：专注于任务调度和生命周期管理

### 5.2 资源利用
- 任务可以按照各自的时间表交错执行
- 避免长时间占用资源
- 提高系统整体吞吐量

### 5.3 灵活性
- 调度器可以灵活调整任务的执行时间
- 支持动态添加、删除、暂停、恢复任务
- 支持调整任务执行优先级

### 5.4 可维护性
- 代码逻辑更清晰，职责明确
- 更容易测试和调试
- 更容易扩展新功能

## 六、示例代码

### 6.1 优化后的完整方法

```python
async def run_once(self) -> bool:
    """
    执行一次任务（单次执行，不包含循环）
    
    Returns:
        bool: 是否应该继续执行
            - True: 任务未到期，可以继续调度
            - False: 任务已到期，不应再执行
    """
    # 1. 检查任务是否已到期
    if datetime.date.today() >= self.task_end_time:
        logger.info(f"任务 {self.task_id} 已到期，不再执行")
        return False
    
    # 2. 检查任务是否是暂停状态
    if self.task_switch.get('state') == 'PAUSE':
        logger.debug(f"任务 {self.task_id} 第 {self.round_num} 轮次暂停")
        return True
    
    # 3. 检查任务是否在执行时间区间内
    if not self._check_time_valid():
        logger.debug(f"任务 {self.task_id} 第 {self.round_num} 轮次未执行，不在执行时间范围内")
        return True
    
    # 4. 执行任务
    logger.info(f"任务 {self.task_id} 第 {self.round_num} 轮次开始执行")
    self.round_num += 1
    
    try:
        # 检查mcp服务
        self._mcp_service_check()
        
        # 部署cookies
        user_cookies_file = os.path.join(
            get_user_cookies_path(self.xhs_account_id), 
            "cookies.json"
        )
        try:
            self._dispatch_cookies(
                source_path=user_cookies_file,
                destination_path=COOKIE_TARGET_PATH
            )
        except RuntimeError as e:
            logger.warning(f"无法找到该账户cookies储备，删除当前cookies，准备重新登陆，错误: {e}")
            self._clear_cookies()
        
        # 运行agent任务
        try:
            await self.agent.run()
        except Exception as e:
            logger.warning(f"agent任务执行失败，错误：{e}")
        
        # 收尾工作
        try:
            self._close_task()
        except Exception as e:
            logger.error(f"任务收尾工作失败: {e}")
        
        logger.info(f"任务 {self.task_id} 第 {self.round_num-1} 轮次执行完成")
        return True
        
    except Exception as e:
        logger.error(f"任务 {self.task_id} 执行过程中发生异常: {e}", exc_info=True)
        return datetime.date.today() < self.task_end_time
```

### 6.2 调度器调用示例

```python
# 调度器中的调用
async def execute_task(task_info: TaskInfo):
    async with self.execution_lock:
        task_info.status = TaskStatus.RUNNING
        should_continue = await task_info.task_manager.run_once()
        
        task_info.last_execution_time = datetime.datetime.now()
        
        if should_continue:
            task_info.next_execution_time = self._calculate_next_execution_time(task_info)
            task_info.status = TaskStatus.PENDING
        else:
            task_info.next_execution_time = None
            task_info.status = TaskStatus.COMPLETED
```

## 七、总结

通过将 `TaskManager.run()` 改为 `run_once()`，实现了：

1. **职责分离**：TaskManager 专注于执行，调度器专注于调度
2. **资源优化**：任务可以交错执行，提高资源利用率
3. **灵活性提升**：调度器可以灵活控制任务的执行时机
4. **代码简化**：移除了循环和等待逻辑，代码更清晰

这是一个符合单一职责原则和关注点分离的优秀设计。
