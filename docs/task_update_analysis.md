# 任务属性调整功能分析与方案

## 一、当前架构分析

### 1.1 任务属性存储位置

任务属性存储在三个位置：

1. **TaskInfo** (内存对象)
   - `task_id`, `account_id`, `account_name`, `task_type`
   - `interval`, `valid_time_range`, `task_end_time`
   - `status`, `last_execution_time`, `next_execution_time`
   - `kwargs` (包含 user_query, user_topic, user_style, user_target_audience 等)

2. **Task_Manager_Context.meta** (持久化文件: `app/manager/data/meta_{task_id}.json`)
   - `user_query`, `user_topic`, `user_style`, `user_target_audience`
   - `interval`, `valid_time_range`, `task_end_time`
   - `task_type`, `sys_type`
   - `step` (执行历史)

3. **TaskDispatcher 的 dispatch_config.json** (持久化文件)
   - 所有任务的完整配置
   - 任务状态和调度信息

### 1.2 需要可调整的属性

根据 `TaskCreateRequest`，以下属性应该可调整：

- ✅ **user_topic**: 帖子主题
- ✅ **user_style**: 内容风格
- ✅ **user_target_audience**: 目标受众
- ✅ **task_end_time**: 任务结束时间
- ✅ **interval**: 执行间隔（秒）
- ✅ **valid_time_range**: 有效时间范围 [start_hour, end_hour]

**不可调整的属性**（涉及任务身份和状态）：
- ❌ `task_id`: 任务唯一标识
- ❌ `account_id`: 账户ID（与任务身份绑定）
- ❌ `account_name`: 账户名称（与账户ID绑定）
- ❌ `task_type`: 任务类型
- ❌ `sys_type`: 系统类型

### 1.3 属性使用时机

- **执行时使用**（影响下次执行）：
  - `user_topic`, `user_style`, `user_target_audience` → 在 `TaskManager.run_once()` 中使用，影响内容生成
  - `interval`, `valid_time_range`, `task_end_time` → 在 `TaskDispatcher._calculate_next_execution_time()` 中使用，影响调度

## 二、实现难度评估

### 2.1 技术难度：**中等**

**复杂度分析：**

1. **数据一致性（高）** ⚠️
   - 需要同时更新 3 个存储位置
   - 需要确保数据同步，避免不一致

2. **状态管理（中）** ⚠️
   - 运行中的任务：属性变更是否立即生效？
   - 暂停/已完成的任务：可以随时更新

3. **属性验证（低）** ✅
   - 使用 Pydantic 模型验证
   - 与创建任务的验证逻辑相同

4. **调度重新计算（中）** ⚠️
   - 如果修改 `interval` 或 `valid_time_range`，需要重新计算 `next_execution_time`
   - 如果修改 `task_end_time`，可能需要取消任务

5. **持久化（低）** ✅
   - 已有保存机制，只需调用

### 2.2 代码修改量：**中等**

需要修改的文件：
- `app/api/models.py` - 添加 `TaskUpdateRequest` 模型（+20 行）
- `app/api/routers/tasks.py` - 添加 `PATCH /tasks/{task_id}` 接口（+80 行）
- `app/manager/task_dispatcher.py` - 添加 `update_task()` 方法（+100 行）
- `app/manager/task_context.py` - 可能需要添加 `update_meta()` 方法（+30 行）
- `app/api/static/index.html` - 添加前端编辑界面（+200 行，可选）

总计：约 **430 行代码**（不含前端）

## 三、实现方案

### 3.1 方案概述

采用 **PATCH 接口 + 部分更新** 的方式：

1. 用户通过 API 提交要更新的属性（部分字段，非必填）
2. 后端验证并更新三个存储位置
3. 如果修改了调度相关属性，重新计算下次执行时间
4. 返回更新后的任务信息

### 3.2 详细设计

#### 3.2.1 API 设计

```python
# 请求模型
class TaskUpdateRequest(BaseModel):
    """更新任务请求模型"""
    user_query: Optional[str] = None
    user_topic: Optional[str] = None
    user_style: Optional[str] = None
    user_target_audience: Optional[str] = None
    task_end_time: Optional[str] = None  # ISO日期格式
    interval: Optional[int] = None  # 执行间隔（秒）
    valid_time_range: Optional[List[int]] = None  # [start_hour, end_hour]

# API 端点
PATCH /api/v1/tasks/{task_id}
```

#### 3.2.2 实现流程

```
1. 接收更新请求
   ↓
2. 验证任务是否存在
   ↓
3. 检查任务状态（如果运行中，允许更新但不立即生效，下次执行时生效）
   ↓
4. 验证更新数据（使用 Pydantic 验证）
   ↓
5. 更新 Task_Manager_Context.meta
   ↓
6. 更新 TaskInfo 对象
   ↓
7. 如果修改了 interval/valid_time_range/task_end_time：
   - 重新计算 next_execution_time
   ↓
8. 保存 TaskDispatcher 状态到 dispatch_config.json
   ↓
9. 返回更新后的任务信息
```

#### 3.2.3 关键实现点

1. **TaskDispatcher.update_task()** 方法
   - 更新 TaskInfo 对象
   - 更新 Task_Manager_Context.meta
   - 重新计算调度时间（如果需要）
   - 保存状态

2. **Task_Manager_Context.update_meta()** 方法（可选）
   - 更新 meta 字典中的指定字段
   - 自动保存到文件

3. **状态处理**
   - 运行中的任务：允许更新，但属性在下一次执行时生效
   - 其他状态：立即更新

### 3.3 实现步骤（建议）

#### 第一阶段：后端 API（2-3 小时）
1. ✅ 添加 `TaskUpdateRequest` 模型
2. ✅ 实现 `TaskDispatcher.update_task()` 方法
3. ✅ 添加 `PATCH /tasks/{task_id}` API 端点
4. ✅ 测试 API 功能

#### 第二阶段：前端界面（3-4 小时，可选）
1. 添加"编辑任务"按钮
2. 实现编辑表单（复用创建任务的表单）
3. 调用更新 API
4. 刷新任务列表

#### 第三阶段：优化（1-2 小时，可选）
1. 添加属性变更日志
2. 添加变更历史记录
3. 优化用户体验

## 四、风险评估

### 4.1 潜在问题

1. **数据不一致**
   - 风险：三个存储位置更新不同步
   - 缓解：在同一个方法中更新，使用事务性保存

2. **运行中任务**
   - 风险：属性变更导致当前执行异常
   - 缓解：运行中的任务，属性在下一次执行时生效

3. **调度时间计算**
   - 风险：修改 interval 后 next_execution_time 计算错误
   - 缓解：调用已有的 `_calculate_next_execution_time()` 方法

### 4.2 兼容性

- ✅ 向后兼容：不影响现有功能
- ✅ 可选功能：不强制使用
- ✅ 数据格式：与现有格式一致

## 五、推荐方案

### 5.1 推荐：分阶段实现

**阶段1：核心功能（必须）**
- 实现后端 API
- 支持所有可调整属性的更新
- 基本验证和错误处理

**阶段2：前端界面（推荐）**
- 添加编辑按钮和表单
- 提升用户体验

**阶段3：增强功能（可选）**
- 变更历史记录
- 变更通知
- 批量更新

### 5.2 实现优先级

1. **高优先级**（核心功能）
   - user_topic, user_style, user_target_audience（内容相关）
   - task_end_time（任务结束时间）

2. **中优先级**（调度相关）
   - interval（执行间隔）
   - valid_time_range（有效时间范围）

3. **低优先级**（可选）
   - user_query（用户查询）

## 六、总结

- **技术难度**：中等（需要处理数据一致性和状态管理）
- **代码量**：约 430 行（不含前端）
- **实现时间**：后端 2-3 小时，前端 3-4 小时
- **风险等级**：低-中等（有可行的缓解措施）
- **推荐度**：⭐⭐⭐⭐（高，提升用户体验）
