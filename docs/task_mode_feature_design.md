# 任务模式特性设计文档

## 一、需求概述

为每个任务增加"模式"属性，支持三种执行模式，不同模式下智能体的行为不同：
- **标准模式**：先互动（搜索主题相关笔记并点赞收藏评论），再评论自己的历史笔记，最后发布笔记
- **互动模式**：只执行互动操作（搜索主题相关笔记并点赞收藏评论），不发布笔记
- **发布模式**：只发布笔记，不执行互动操作

## 二、当前状态分析

### 2.1 当前智能体行为（`app/agents/xiaohongshu/agent.py`）

当前智能体的 `run()` 方法执行流程（接近标准模式）：
1. 获取自己历史发布的笔记标题列表
2. 对历史笔记进行评论互动（循环遍历历史笔记，生成评论并发表）
3. 生成新的笔记内容
4. 生成笔记配图
5. 发布新笔记

**当前存在的问题：**
- 互动逻辑单一：只评论自己的历史笔记，没有搜索主题相关的其他笔记进行互动
- 缺少模式区分：所有任务都执行相同的流程，无法根据需求选择不同的执行策略

### 2.2 数据结构现状

- `TaskInfo` (`app/manager/task_info.py`)：任务信息数据类，目前没有模式字段
- `TaskCreateRequest` / `TaskUpdateRequest` (`app/api/models.py`)：API请求模型，没有模式字段
- `TaskManager` (`app/manager/task_manager.py`)：任务管理器，负责执行任务

## 三、技术实现方案

### 3.1 数据结构变更

#### 3.1.1 定义任务模式枚举

**文件：`app/data/constants.py` 或新建 `app/manager/task_mode.py`**

```python
from enum import Enum

class TaskMode(str, Enum):
    """任务执行模式枚举"""
    STANDARD = "standard"    # 标准模式：互动 + 发布
    INTERACTION = "interaction"  # 互动模式：仅互动
    PUBLISH = "publish"      # 发布模式：仅发布
```

#### 3.1.2 更新 `TaskInfo` 数据类

**文件：`app/manager/task_info.py`**

在 `TaskInfo` 类中添加 `mode` 字段：

```python
from app.manager.task_mode import TaskMode  # 或从 constants 导入

@dataclass
class TaskInfo:
    # ... 现有字段 ...
    mode: TaskMode = TaskMode.STANDARD  # 任务执行模式，默认为标准模式
```

#### 3.1.3 更新 API 模型

**文件：`app/api/models.py`**

1. **`TaskCreateRequest`** 添加 `mode` 字段：
```python
from app.manager.task_mode import TaskMode

class TaskCreateRequest(BaseModel):
    # ... 现有字段 ...
    mode: Optional[TaskMode] = Field(default=TaskMode.STANDARD, description="任务执行模式", examples=["standard", "interaction", "publish"])
```

2. **`TaskUpdateRequest`** 添加 `mode` 字段：
```python
class TaskUpdateRequest(BaseModel):
    # ... 现有字段 ...
    mode: Optional[TaskMode] = Field(None, description="任务执行模式", examples=["standard", "interaction", "publish"])
```

3. **`TaskInfoResponse`** 添加 `mode` 字段：
```python
class TaskInfoResponse(BaseModel):
    # ... 现有字段 ...
    mode: str = Field(..., description="任务执行模式", example="standard")
```

#### 3.1.4 更新 `TaskManager` 初始化

**文件：`app/manager/task_manager.py`**

在 `__init__` 方法中添加 `mode` 参数处理：

```python
class TaskManager:
    def __init__(self, sys_type, **kwargs):
        # ... 现有代码 ...
        self.mode = kwargs.get('mode', TaskMode.STANDARD)
        # 如果从 context 恢复，从 context 读取 mode
        if self.task_id:
            self.mode = TaskMode(self.context.get('mode', TaskMode.STANDARD.value))
```

### 3.2 智能体逻辑改造

#### 3.2.1 新增主题相关笔记互动方法

**文件：`app/agents/xiaohongshu/agent.py`**

在 `XiaohongshuAgent` 类中新增方法：

```python
async def interact_with_topic_notes(
    self,
    topic: str,
    interaction_count: int = 3
) -> Dict[str, Any]:
    """
    搜索主题相关的笔记并进行互动（点赞、收藏、评论）
    
    Args:
        topic: 主题关键词
        interaction_count: 互动笔记数量，默认3条
        
    Returns:
        互动结果统计
    """
    # 1. 搜索主题相关笔记
    search_results = await self.search_feeds(keyword=topic, limit=interaction_count)
    
    # 2. 解析搜索结果，获取笔记详情
    # 3. 对每条笔记进行点赞、收藏、评论操作
    # 4. 记录互动日志
    
    pass  # TODO: 实现具体逻辑
```

#### 3.2.2 重构 `run()` 方法支持模式切换

**文件：`app/agents/xiaohongshu/agent.py`**

将 `run()` 方法改为根据模式执行不同逻辑：

```python
async def run(self) -> Any:
    """小红书智能体主执行逻辑（支持模式切换）"""
    try:
        await self.ensure_connected()
        
        # 获取任务模式（从 kwargs 或 context 获取）
        mode = getattr(self, 'mode', TaskMode.STANDARD)
        
        if mode == TaskMode.STANDARD:
            # 标准模式：互动 + 发布
            # 1. 搜索主题相关笔记并互动
            await self.interact_with_topic_notes(self.user_topic)
            # 2. 评论自己的历史笔记
            await self.comment_own_notes()
            # 3. 发布新笔记
            await self.publish_new_note()
            
        elif mode == TaskMode.INTERACTION:
            # 互动模式：仅互动
            # 1. 搜索主题相关笔记并互动
            await self.interact_with_topic_notes(self.user_topic)
            # 2. 评论自己的历史笔记
            await self.comment_own_notes()
            
        elif mode == TaskMode.PUBLISH:
            # 发布模式：仅发布
            # 1. 发布新笔记
            await self.publish_new_note()
            
    except Exception as e:
        logger.error(f"执行失败: {e}")
        raise
```

#### 3.2.3 抽取公共方法

将现有逻辑拆分为独立方法，便于复用：

```python
async def comment_own_notes(self) -> None:
    """评论自己的历史笔记（抽取自原 run 方法）"""
    previous_notes_title = await self.get_n_last_notes_title(self.comment_note_nums)
    # ... 原有逻辑 ...

async def publish_new_note(self) -> None:
    """发布新笔记（抽取自原 run 方法）"""
    # ... 原有发布逻辑 ...
```

#### 3.2.4 传递模式参数给 Agent

**文件：`app/manager/task_manager.py`**

在 `run_once` 方法中，将 `mode` 传递给 Agent：

```python
async def run_once(self, skip_time_check: bool = False) -> bool:
    # ... 现有代码 ...
    
    # 初始化 Agent 时传递 mode
    self.agent = XiaohongshuAgent(
        context=self.context,
        llm=self.llm_service,
        user_name=self.xhs_account_name,
        user_id=self.xhs_account_id,
        task_id=self.task_id,
        mode=self.mode,  # 传递模式参数
        # ... 其他参数 ...
    )
```

### 3.3 前端UI实现

#### 3.3.1 更新 TypeScript 类型定义

**文件：`frontend/src/types/task.ts`**

```typescript
export type TaskMode = 'standard' | 'interaction' | 'publish';

export interface Task {
  // ... 现有字段 ...
  mode: TaskMode;
}

export interface TaskCreateRequest {
  // ... 现有字段 ...
  mode?: TaskMode;
}

export interface TaskUpdateRequest {
  // ... 现有字段 ...
  mode?: TaskMode;
}
```

#### 3.3.2 左侧配置面板添加模式选择器

**文件：`frontend/src/components/Layout/Sidebar.tsx`**

在左侧设置面板中添加模式选择组件（建议使用 Ant Design 的 `Radio.Group` 或 `Select`）：

```tsx
import { Radio } from 'antd';

const TaskModeRadio: React.FC<{ mode: TaskMode; onChange: (mode: TaskMode) => void }> = ({ mode, onChange }) => {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ marginBottom: 8, fontWeight: 500 }}>执行模式</div>
      <Radio.Group
        value={mode}
        onChange={(e) => onChange(e.target.value)}
        optionType="button"
        buttonStyle="solid"
      >
        <Radio.Button value="standard">标准模式</Radio.Button>
        <Radio.Button value="interaction">互动模式</Radio.Button>
        <Radio.Button value="publish">发布模式</Radio.Button>
      </Radio.Group>
      <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
        {mode === 'standard' && '互动 + 发布笔记'}
        {mode === 'interaction' && '仅执行互动操作'}
        {mode === 'publish' && '仅发布笔记'}
      </div>
    </div>
  );
};
```

**布局建议：**
- 放在"执行间隔"和"有效时间范围"之间
- 使用 `Radio.Group` 的 `optionType="button"` 样式，更美观
- 添加模式说明文字，帮助用户理解

#### 3.3.3 任务卡片添加模式图标

**文件：`frontend/src/components/TaskCard/TaskCard.tsx`**

在任务卡片标题区域添加模式图标：

```tsx
import { Tooltip } from 'antd';
import { 
  StarOutlined,      // 标准模式图标
  MessageOutlined,   // 互动模式图标
  SendOutlined       // 发布模式图标
} from '@ant-design/icons';

const getModeIcon = (mode: TaskMode) => {
  switch (mode) {
    case 'standard':
      return <StarOutlined style={{ color: '#1890ff' }} />;
    case 'interaction':
      return <MessageOutlined style={{ color: '#52c41a' }} />;
    case 'publish':
      return <SendOutlined style={{ color: '#faad14' }} />;
    default:
      return null;
  }
};

const getModeLabel = (mode: TaskMode) => {
  switch (mode) {
    case 'standard':
      return '标准模式：互动 + 发布';
    case 'interaction':
      return '互动模式：仅互动';
    case 'publish':
      return '发布模式：仅发布';
    default:
      return '';
  }
};

// 在任务卡片标题中使用
<Tooltip title={getModeLabel(task.mode)}>
  {getModeIcon(task.mode)}
</Tooltip>
```

**布局建议：**
- 图标放在任务卡片标题的右侧（账户名称之后）
- 使用 `Tooltip` 组件，鼠标悬停时显示模式说明
- 不同模式使用不同颜色的图标，便于区分

#### 3.3.4 创建/编辑任务表单添加模式选择

**文件：`frontend/src/components/TaskForm/CreateTaskForm.tsx`**  
**文件：`frontend/src/components/TaskForm/EditTaskForm.tsx`**

在表单中添加模式选择字段：

```tsx
import { Radio } from 'antd';

<Form.Item
  label="执行模式"
  name="mode"
  initialValue="standard"
>
  <Radio.Group optionType="button" buttonStyle="solid">
    <Radio.Button value="standard">标准模式</Radio.Button>
    <Radio.Button value="interaction">互动模式</Radio.Button>
    <Radio.Button value="publish">发布模式</Radio.Button>
  </Radio.Group>
</Form.Item>
```

### 3.4 数据持久化

#### 3.4.1 更新 `Task_Manager_Context`

**文件：`app/manager/task_context.py`**

在 `create_new_meta` 和 `_local_load` 中保存/加载 `mode` 字段：

```python
def create_new_meta(self, **kwargs):
    self.meta = {
        # ... 现有字段 ...
        "mode": kwargs.get('mode', 'standard'),  # 默认为标准模式
    }

def _local_load(self):
    # ... 现有代码 ...
    self.mode = self.meta.get("mode", "standard")  # 从 meta 加载 mode
```

#### 3.4.2 更新 `TaskDispatcher` 状态保存

**文件：`app/manager/task_dispatcher.py`**

在 `_save_state` 和 `_load_state` 中处理 `mode` 字段：

```python
def _save_state(self):
    # ... 现有代码 ...
    task_data["mode"] = task_info.mode.value  # 保存模式

def _load_state(self):
    # ... 现有代码 ...
    mode_str = task_data.get("mode", "standard")
    mode = TaskMode(mode_str)  # 恢复模式枚举
```

## 四、待确认问题

### 4.1 模式切换时机

**问题：** 任务正在执行时，如果用户修改了模式，是否立即生效？

**建议：**
- 当前执行中的任务不受影响，继续按原模式执行
- 修改后的模式在下次执行时生效

（我认为修改后的模型在下次执行时生效比较合理）

**需要确认：** ✅ 是否符合预期？

### 4.2 互动笔记数量配置

**问题：** "互动模式"和"标准模式"中搜索主题相关笔记的数量是否可配置？

**建议：**
- 暂时固定为 3-5 条笔记
- 未来可以考虑作为任务配置项（类似 `comment_note_nums`）
（我认为需要可以配置，但是要设定默认值为3，并且最大值为5，避免过度评论）

**需要确认：** 互动笔记数量是否有要求？

### 4.3 互动操作顺序

**问题：** 对主题相关笔记进行互动时，点赞、收藏、评论的操作顺序是什么？

**建议：**
- 顺序：点赞 → 收藏 → 评论（符合用户浏览习惯）
- 每条笔记随机间隔 5-20 秒，避免操作过快
（这个建议非常好）

**需要确认：** 操作顺序和间隔时间是否符合预期？

### 4.4 搜索关键词策略

**问题：** "互动模式"中搜索主题相关笔记时，使用什么关键词？

**建议：**
- 优先使用 `user_topic`（任务主题）
- 如果没有设置主题，使用 `user_query` 作为关键词
- 如果两者都没有，可以提示用户必须设置主题
（任务主题可以使用，但是不要用user_query，因为user_query中的内容可能和主题无关，而且可能比较长，不适合做关键词。我认为可以在前端任务主题表单加上必填提醒，并可以加上用户在资料中提供的text中的随机标题词汇来作为关键词的补充）

**需要确认：** 搜索策略是否合理？

### 4.5 评论内容生成策略

**问题：** 对主题相关笔记进行评论时，评论内容如何生成？

**建议：**
- 复用现有的 `generate_comment` 方法
- 传入笔记内容和现有评论列表，由 LLM 生成评论
（你的建议很好）

**需要确认：** 是否需要针对主题相关笔记优化评论生成逻辑？

### 4.6 模式图标设计

**问题：** 前端任务卡片上的模式图标是否使用 Ant Design 内置图标？

**建议：**
- 标准模式：`StarOutlined`（星标，表示完整流程）
- 互动模式：`MessageOutlined`（消息，表示互动）
- 发布模式：`SendOutlined`（发送，表示发布）
（可以的）

**需要确认：** 图标选择是否符合预期，是否需要自定义图标？

### 4.7 向后兼容性

**问题：** 现有任务没有 `mode` 字段，如何处理？

**建议：**
- 默认值设为 `TaskMode.STANDARD`（标准模式）
- 在 `_load_state` 和 `_local_load` 中，如果 `mode` 不存在，默认为标准模式
（好的）

**需要确认：** ✅ 默认标准模式是否合理？

### 4.8 模式说明文案

**问题：** 前端UI中的模式说明文字是否需要更详细的描述？

**建议：**
- 左侧配置面板：简短说明（如"互动 + 发布笔记"）
- 创建/编辑表单：可以添加更详细的帮助文字
- 鼠标悬停：显示完整说明（如"标准模式：先互动后发布"）
（非常好）

**需要确认：** 文案是否清晰易懂？

## 五、实施计划

### 阶段一：后端数据结构（1-2小时）
1. 定义 `TaskMode` 枚举
2. 更新 `TaskInfo`、`TaskCreateRequest`、`TaskUpdateRequest`、`TaskInfoResponse`
3. 更新 `TaskManager` 初始化逻辑
4. 更新 `TaskDispatcher` 的状态保存/加载逻辑

### 阶段二：智能体逻辑改造（3-4小时）
1. 实现 `interact_with_topic_notes` 方法
2. 抽取 `comment_own_notes` 和 `publish_new_note` 方法
3. 重构 `run()` 方法支持模式切换
4. 测试三种模式的执行逻辑

### 阶段三：前端UI实现（2-3小时）
1. 更新 TypeScript 类型定义
2. 在左侧配置面板添加模式选择器
3. 在任务卡片添加模式图标
4. 在创建/编辑表单添加模式选择
5. 测试模式切换和显示

### 阶段四：测试和优化（2-3小时）
1. 测试模式切换功能
2. 测试数据持久化（创建、编辑、恢复）
3. 测试三种模式的执行流程
4. 优化UI显示和交互体验

**总计预估时间：8-12小时**

## 六、风险评估

### 6.1 技术风险

- **低风险：** 数据结构变更和模式切换逻辑相对简单
- **中风险：** 智能体逻辑改造需要仔细测试，确保不影响现有功能

### 6.2 兼容性风险

- **低风险：** 通过默认值处理，现有任务自动使用标准模式，向后兼容

### 6.3 用户体验风险

- **低风险：** UI改动较小，主要是添加选择器和图标，不影响现有流程

## 七、参考资料

- `app/agents/xiaohongshu/agent.py`：智能体执行逻辑
- `app/manager/task_info.py`：任务信息数据结构
- `app/api/models.py`：API请求/响应模型
- `app/manager/task_manager.py`：任务管理器
- `app/manager/task_dispatcher.py`：任务调度器

---

**文档版本：** v1.0  
**创建日期：** 2026-01-17  
**最后更新：** 2026-01-17
