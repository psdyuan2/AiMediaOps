# 注册码激活功能开发方案

## 一、功能概述

实现产品注册码激活功能，支持免费试用和付费激活两种模式。未激活用户可以体验基础功能（限制1个任务、固定执行间隔2小时、无法立即执行），以促进产品转化。激活后的配置信息将加密存储在本地文件中，服务启动时自动读取并验证，根据配置对产品使用进行限制。

## 二、功能需求

### 2.1 后端需求

1. **注册码验证与激活**
   - 调用注册机服务验证注册码
   - 将激活后的配置数据加密存储到本地文件
   - 提供激活状态查询接口
   - 提供激活接口

2. **配置管理**
   - 服务启动时读取加密配置文件
   - 验证激活状态和到期时间
   - 根据配置限制任务数量等功能

3. **使用限制**
   - **未激活用户（免费试用）**：
     - 只能创建 1 个任务
     - 执行间隔固定为 2 小时（7200 秒），无法调整
     - 无法立即执行任务
     - 可以使用其他基础功能（查看任务、暂停/恢复、删除等）
   - **已激活用户**：
     - 限制可创建的任务总数（基于 `task_num` 配置）
     - 可以自定义执行间隔（15分钟-3小时）
     - 可以立即执行任务
     - 检查激活是否过期（基于 `end_time` 配置）
   - 在创建任务、执行任务时进行限制检查

### 2.2 前端需求

1. **侧边栏按钮**
   - 将"查看当前套餐"按钮改为可点击
   - 点击后弹出套餐信息卡片

2. **套餐信息卡片**
   - 显示当前激活状态（已激活/未激活/已过期）
   - **未激活状态**：显示"免费试用 - 可创建1个任务"
   - **已激活状态**：显示产品到期时间（`end_time`）、可用任务数量（`task_num`）
   - 显示"激活码激活"按钮
   - 显示"激活码购买"按钮

3. **未激活用户的UI限制**
   - 侧边栏执行间隔滑块禁用，固定显示"2小时"
   - 任务列表中的"立即执行"按钮禁用
   - 任务创建表单中执行间隔字段禁用，固定为2小时
   - 显示友好的提示信息，引导用户激活

4. **激活码激活对话框**
   - 输入框用于输入注册码
   - 提交后调用后端激活接口
   - 显示激活结果

5. **激活码购买文档**
   - 类似帮助文档的实现方式
   - 链接到 Markdown 文档

## 三、技术实现方案

### 3.1 后端实现

#### 3.1.1 目录结构

```
app/
├── core/
│   └── license_manager.py      # 注册码管理器（新增）
├── api/
│   └── routers/
│       └── license.py          # 注册码相关路由（新增）
└── utils/
    └── encryption.py           # 加密工具（新增，可选）
```

#### 3.1.2 注册码管理器 (`app/core/license_manager.py`)

**功能**：
- 管理注册码验证和激活
- 加密存储和读取激活配置
- 验证激活状态和限制

**主要类和方法**：

```python
class LicenseManager:
    """注册码管理器"""
    
    def __init__(self, config_file_path: str = "license_config.encrypted"):
        """初始化注册码管理器"""
        pass
    
    def verify_license(self, license_code: str) -> dict:
        """验证注册码并获取配置"""
        # 调用注册机服务: POST http://175.24.40.127/api/licenses/verify
        # 请求体: {"product_id": 1, "license_code": license_code}
        # 返回: {"success": true, "config": {...}}
        pass
    
    def activate(self, license_code: str) -> dict:
        """激活注册码并保存配置"""
        # 1. 验证注册码
        # 2. 加密保存配置到文件
        # 3. 返回激活结果
        pass
    
    def load_config(self) -> Optional[dict]:
        """从加密文件加载配置"""
        pass
    
    def save_config(self, config: dict) -> bool:
        """加密保存配置到文件"""
        pass
    
    def is_activated(self) -> bool:
        """检查是否已激活"""
        pass
    
    def is_expired(self) -> bool:
        """检查是否已过期"""
        pass
    
    def get_remaining_tasks(self) -> int:
        """获取剩余可用任务数量"""
        pass
    
    def can_create_task(self) -> bool:
        """检查是否可以创建新任务"""
        pass
    
    def get_config(self) -> Optional[dict]:
        """获取当前配置"""
        pass
    
    def get_max_tasks(self) -> int:
        """获取最大任务数量
        未激活返回1，已激活返回配置的task_num
        """
        pass
    
    def get_interval_limit(self) -> Optional[int]:
        """获取执行间隔限制
        未激活返回7200（2小时），已激活返回None（无限制）
        """
        pass
    
    def can_execute_immediately(self) -> bool:
        """检查是否可以立即执行任务
        未激活返回False，已激活返回True
        """
        pass
```

**加密方案**：
- 使用 Python `cryptography` 库的 Fernet 对称加密
- 密钥可以从环境变量或固定密钥派生（用于本地加密）
- 配置文件路径：`license_config.encrypted`（项目根目录）

#### 3.1.3 注册码路由 (`app/api/routers/license.py`)

**接口设计**：

```python
# GET /api/v1/license/status
# 获取激活状态和配置信息
# 响应: {
#   "activated": true,
#   "config": {
#     "end_time": "2024-12-31T23:59:59",
#     "task_num": 100,
#     "is_free": false,
#     "price": 100
#   },
#   "remaining_tasks": 95,
#   "is_expired": false
# }

# POST /api/v1/license/activate
# 激活注册码
# 请求体: {"license_code": "xxx"}
# 响应: {
#   "success": true,
#   "message": "激活成功",
#   "config": {...}
# }
```

#### 3.1.4 服务启动时验证

在 `service/start_api.py` 或 `app/api/main.py` 中：

```python
from app.core.license_manager import LicenseManager

# 服务启动时
license_manager = LicenseManager()
if not license_manager.is_activated():
    logger.warning("⚠️ 产品未激活，请先激活注册码")
elif license_manager.is_expired():
    logger.warning("⚠️ 产品已过期，请重新激活")
else:
    logger.info("✅ 产品激活状态正常")
```

#### 3.1.5 任务创建限制

在 `app/api/routers/tasks.py` 的 `create_task` 方法中：

```python
from app.core.license_manager import get_license_manager

@router.post("/tasks/")
async def create_task(...):
    license_manager = get_license_manager()
    
    # 检查过期状态（无论是否激活，过期都不允许创建任务）
    if license_manager.is_activated() and license_manager.is_expired():
        raise LicenseExpiredError(
            end_time=license_manager.get_config().get("end_time", "")
        )
    
    # 检查任务数量限制
    current_count = len(dispatcher.list_tasks())
    max_tasks = license_manager.get_max_tasks()  # 未激活返回1，已激活返回task_num
    
    if current_count >= max_tasks:
        if not license_manager.is_activated():
            raise HTTPException(
                status_code=403,
                detail=f"免费试用版最多只能创建 {max_tasks} 个任务。请激活产品以创建更多任务。",
                headers={"X-License-Limit": "free_trial"}
            )
        else:
            raise TaskLimitReachedError(
                max_tasks=max_tasks,
                current_tasks=current_count,
                remaining=0
            )
    
    # 检查执行间隔限制（未激活用户固定为2小时）
    if not license_manager.is_activated():
        # 强制设置执行间隔为2小时（7200秒）
        if request_body.interval != 7200:
            request_body.interval = 7200
            logger.info("免费试用版：执行间隔已自动设置为2小时（7200秒）")
    else:
        # 已激活用户：验证间隔是否在允许范围内（15分钟-3小时）
        if request_body.interval < 900 or request_body.interval > 10800:
            raise HTTPException(
                status_code=400,
                detail="执行间隔必须在900秒（15分钟）到10800秒（3小时）之间"
            )
    
    # 继续创建任务...
```

#### 3.1.6 立即执行任务限制

在 `app/api/routers/tasks.py` 的 `execute_task_immediately` 方法中：

```python
@router.post("/tasks/{task_id}/execute")
async def execute_task_immediately(
    task_id: str,
    license_manager: LicenseManager = Depends(get_license_manager)
):
    # 检查是否可以立即执行（未激活用户不允许）
    if not license_manager.can_execute_immediately():
        raise HTTPException(
            status_code=403,
            detail="免费试用版不支持立即执行功能，请激活产品以使用此功能。",
            headers={"X-License-Limit": "free_trial"}
        )
    
    # 继续执行任务...
```

### 3.2 前端实现

#### 3.2.1 目录结构

```
frontend/src/
├── components/
│   ├── LicenseCard/              # 套餐信息卡片（新增）
│   │   ├── LicenseCard.tsx
│   │   └── index.ts
│   └── LicenseActivateDialog/    # 激活码激活对话框（新增）
│       ├── LicenseActivateDialog.tsx
│       └── index.ts
├── services/
│   └── licenseService.ts         # 注册码服务（新增）
└── types/
    └── license.ts                # 注册码类型定义（新增）
```

#### 3.2.2 修改侧边栏 (`frontend/src/components/Layout/Sidebar.tsx`)

**修改点**：
1. 将"查看当前套餐"按钮的 `disabled` 属性改为 `false`
2. 添加点击事件处理函数
3. 引入 `LicenseCard` 组件
4. 添加状态管理（控制卡片显示/隐藏）
5. **新增**：根据激活状态禁用/启用执行间隔滑块
6. **新增**：未激活时显示固定2小时的提示

```tsx
import { useLicenseStore } from '@/store/licenseStore';  // 新增

const Sidebar: React.FC = () => {
  const { licenseStatus } = useLicenseStore();
  const isActivated = licenseStatus?.activated ?? false;
  const [licenseCardVisible, setLicenseCardVisible] = useState(false);
  
  // ... 其他代码 ...
  
  return (
    <Sider>
      {/* ... 其他组件 ... */}
      
      {/* 执行间隔滑块 - 未激活时禁用 */}
      <div style={{ marginBottom: 24 }}>
        <label>
          <span>执行间隔</span>
          {!isActivated && (
            <span style={{ fontSize: 12, color: '#ff9800', marginLeft: 8 }}>
              (免费试用：固定2小时)
            </span>
          )}
        </label>
        <Slider
          min={900}
          max={10800}
          step={900}
          value={interval}
          onChange={handleIntervalChange}
          disabled={!selectedTask || !isActivated}  // 未激活时禁用
          marks={/* ... */}
        />
        {!isActivated && interval !== 7200 && (
          <div style={{ color: '#ff9800', fontSize: 12, marginTop: 4 }}>
            免费试用版执行间隔固定为2小时
          </div>
        )}
      </div>
      
      {/* ... 其他组件 ... */}
      
      <Button
        icon={<ShoppingOutlined />}
        block
        onClick={() => setLicenseCardVisible(true)}
      >
        查看当前套餐
      </Button>

      <LicenseCard 
        open={licenseCardVisible}
        onClose={() => setLicenseCardVisible(false)}
      />
    </Sider>
  );
};
```

#### 3.2.3 套餐信息卡片 (`frontend/src/components/LicenseCard/LicenseCard.tsx`)

**功能**：
- 显示激活状态、到期时间、可用任务数量
- 提供"激活码激活"和"激活码购买"按钮
- 使用 Popover 或 Card 组件显示在按钮旁边

**设计**：
- 使用 Ant Design 的 `Popover` 组件，定位在按钮旁边
- 卡片内容：
  - 激活状态（已激活/未激活/已过期）
  - 到期时间
  - 可用任务数量 / 总任务数量
  - 两个操作按钮

#### 3.2.4 激活码激活对话框 (`frontend/src/components/LicenseActivateDialog/LicenseActivateDialog.tsx`)

**功能**：
- 输入注册码
- 调用激活接口
- 显示激活结果
- 激活成功后刷新套餐信息

**设计**：
- 使用 Ant Design 的 `Modal` 组件
- 表单包含一个输入框（注册码）
- 提交后显示加载状态
- 成功/失败后显示相应提示

#### 3.2.5 注册码服务 (`frontend/src/services/licenseService.ts`)

```typescript
export interface LicenseStatus {
  success: boolean;
  activated: boolean;
  expired: boolean;
  config: {
    end_time?: string;
    task_num?: number;
    is_free?: boolean;
    price?: number;
  } | null;
  remaining_tasks: number;
  current_tasks: number;
  max_tasks: number;  // 最大任务数（未激活为1，已激活为task_num）
  is_free_trial: boolean;  // 是否为免费试用
}

// 获取激活状态
export const getLicenseStatus = async (): Promise<LicenseStatus> => {
  // GET /api/v1/license/status
  const response = await api.get<LicenseStatus>('/license/status');
  return response;
};

// 激活注册码
export const activateLicense = async (licenseCode: string): Promise<ActivateResponse> => {
  // POST /api/v1/license/activate
  // body: { license_code: licenseCode }
  const response = await api.post<ActivateResponse>('/license/activate', {
    license_code: licenseCode
  });
  return response;
};
```

#### 3.2.6 注册码状态管理 (`frontend/src/store/licenseStore.ts`)

**新增**：创建注册码状态管理 Store

```typescript
import { create } from 'zustand';
import { getLicenseStatus, activateLicense } from '@/services/licenseService';
import type { LicenseStatus } from '@/services/licenseService';
import { message } from 'antd';

interface LicenseStore {
  licenseStatus: LicenseStatus | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchLicenseStatus: () => Promise<void>;
  activate: (licenseCode: string) => Promise<boolean>;
}

export const useLicenseStore = create<LicenseStore>((set, get) => ({
  licenseStatus: null,
  loading: false,
  error: null,
  
  fetchLicenseStatus: async () => {
    set({ loading: true, error: null });
    try {
      const status = await getLicenseStatus();
      set({ licenseStatus: status, loading: false });
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || error.message || '获取激活状态失败';
      set({ error: errorMsg, loading: false });
      // 不显示错误，因为未激活是正常状态
    }
  },
  
  activate: async (licenseCode: string) => {
    set({ loading: true, error: null });
    try {
      await activateLicense(licenseCode);
      message.success('激活成功！');
      // 重新获取状态
      await get().fetchLicenseStatus();
      return true;
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || error.message || '激活失败';
      set({ error: errorMsg, loading: false });
      message.error(errorMsg);
      return false;
    }
  },
}));
```

#### 3.2.7 修改任务创建表单 (`frontend/src/components/TaskForm/CreateTaskForm.tsx`)

**新增**：在表单中根据激活状态禁用执行间隔字段

```tsx
import { useLicenseStore } from '@/store/licenseStore';

export const CreateTaskForm: React.FC<CreateTaskFormProps> = ({ ... }) => {
  const { licenseStatus } = useLicenseStore();
  const isActivated = licenseStatus?.activated ?? false;
  
  // 未激活时，固定间隔为2小时
  const defaultInterval = isActivated ? 3600 : 7200;
  
  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        interval: defaultInterval,
        // ... 其他字段
      });
    }
  }, [open, defaultInterval, form]);
  
  return (
    <Modal>
      <Form form={form}>
        {/* ... 其他字段 ... */}
        
        <Form.Item
          name="interval"
          label="执行间隔（秒）"
          rules={[
            { required: true, message: '请输入执行间隔' },
            { type: 'number', min: 900, message: '最小间隔为15分钟（900秒）' },
            { type: 'number', max: 10800, message: '最大间隔为3小时（10800秒）' }
          ]}
        >
          <InputNumber 
            min={900} 
            max={10800} 
            step={900} 
            style={{ width: '100%' }}
            disabled={!isActivated}  // 未激活时禁用
          />
        </Form.Item>
        {!isActivated && (
          <div style={{ color: '#ff9800', fontSize: 12, marginTop: -16, marginBottom: 16 }}>
            免费试用版执行间隔固定为2小时（7200秒），激活后可自定义
          </div>
        )}
        
        {/* ... 其他字段 ... */}
      </Form>
    </Modal>
  );
};
```

#### 3.2.8 修改任务列表 (`frontend/src/components/TaskList/TaskList.tsx`)

**新增**：在任务列表中禁用"立即执行"按钮（未激活时）

```tsx
import { useLicenseStore } from '@/store/licenseStore';

export const TaskList: React.FC = () => {
  const { licenseStatus } = useLicenseStore();
  const canExecuteImmediately = licenseStatus?.activated ?? false;
  
  return (
    <div>
      {/* ... 任务列表 ... */}
      <Button
        onClick={() => handleExecute(task.task_id)}
        disabled={!canExecuteImmediately}  // 未激活时禁用
        title={!canExecuteImmediately ? '免费试用版不支持立即执行，请激活产品' : ''}
      >
        立即执行
      </Button>
    </div>
  );
};
```

#### 3.2.9 激活码购买文档

**实现方式**：
- 参考 `HelpDialog` 的实现
- 创建新的路由 `/api/v1/help/license-purchase`
- 创建 Markdown 文档 `docs/license_purchase.md`
- 在套餐信息卡片中点击"激活码购买"按钮时打开对话框显示文档

### 3.3 配置文件格式

**加密前（JSON）**：
```json
{
  "product_id": 1,
  "license_code": "xxx",
  "activated_at": "2024-01-01T00:00:00",
  "config": {
    "end_time": "2024-12-31T23:59:59",
    "is_free": false,
    "price": 100,
    "task_num": 100
  }
}
```

**存储**：
- 文件路径：`license_config.encrypted`（项目根目录）
- 加密方式：Fernet 对称加密
- 文件权限：600（仅所有者可读写）

## 四、错误处理与用户提示

### 4.1 后端错误格式统一

为了便于前端处理，所有错误响应统一使用以下格式：

```json
{
  "success": false,
  "error": "错误消息",
  "error_code": "LICENSE_NOT_ACTIVATED",  // 错误代码（可选）
  "error_type": "license"                 // 错误类型（可选）
}
```

**错误类型定义**：
- `license` - 注册码相关错误
- `task_limit` - 任务限制错误
- `validation` - 参数验证错误
- `system` - 系统错误

**注册码相关错误代码**：
- `LICENSE_NOT_ACTIVATED` - 未激活
- `LICENSE_EXPIRED` - 已过期
- `TASK_LIMIT_REACHED` - 任务数量达到上限
- `LICENSE_INVALID` - 注册码无效

### 4.2 后端错误返回示例

#### 4.2.1 未激活错误
```python
raise HTTPException(
    status_code=403,
    detail="产品未激活，请先激活注册码"
)
# 自动被 http_exception_handler 转换为：
# {"success": false, "error": "产品未激活，请先激活注册码"}
```

#### 4.2.2 任务数量限制错误
```python
raise HTTPException(
    status_code=403,
    detail=f"已达到最大任务数量限制（{max_tasks}），无法创建新任务。当前任务数：{current_tasks}，剩余可用：{remaining}"
)
```

#### 4.2.3 过期错误
```python
raise HTTPException(
    status_code=403,
    detail=f"产品已过期，过期时间：{end_time}。请重新激活注册码"
)
```

**注意**：为了支持前端特殊处理，可以在异常处理器中添加错误代码和类型：

```python
# 在 app/api/exceptions.py 中添加自定义异常类

class LicenseNotActivatedError(HTTPException):
    """产品未激活异常"""
    def __init__(self):
        super().__init__(
            status_code=403,
            detail="产品未激活，请先激活注册码"
        )

class LicenseExpiredError(HTTPException):
    """产品已过期异常"""
    def __init__(self, end_time: str):
        super().__init__(
            status_code=403,
            detail=f"产品已过期，过期时间：{end_time}。请重新激活注册码"
        )

class TaskLimitReachedError(HTTPException):
    """任务数量达到上限异常"""
    def __init__(self, max_tasks: int, current_tasks: int, remaining: int):
        super().__init__(
            status_code=403,
            detail=f"已达到最大任务数量限制（{max_tasks}），无法创建新任务。当前任务数：{current_tasks}，剩余可用：{remaining}"
        )
```

然后在异常处理器中识别这些异常，返回带有错误代码的响应：

```python
# 在 app/api/exceptions.py 中改进异常处理器

async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理器"""
    error_data = {
        "success": False,
        "error": exc.detail
    }
    
    # 识别自定义异常，添加错误代码和类型
    if isinstance(exc, LicenseNotActivatedError):
        error_data["error_code"] = "LICENSE_NOT_ACTIVATED"
        error_data["error_type"] = "license"
    elif isinstance(exc, LicenseExpiredError):
        error_data["error_code"] = "LICENSE_EXPIRED"
        error_data["error_type"] = "license"
    elif isinstance(exc, TaskLimitReachedError):
        error_data["error_code"] = "TASK_LIMIT_REACHED"
        error_data["error_type"] = "task_limit"
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_data
    )
```

### 4.3 前端错误拦截器改进

#### 4.3.1 改进 `api.ts` 响应拦截器

```typescript
// frontend/src/services/api.ts

import axios from 'axios';
import { message, Modal } from 'antd';
import type { AxiosInstance, AxiosError } from 'axios';

// 定义错误响应类型
interface ErrorResponse {
  success: false;
  error: string;
  error_code?: string;
  error_type?: string;
}

// 注册码错误代码
const LICENSE_ERROR_CODES = [
  'LICENSE_NOT_ACTIVATED',
  'LICENSE_EXPIRED',
  'TASK_LIMIT_REACHED',
  'LICENSE_INVALID'
];

// 存储激活对话框打开函数（由组件注册）
let openActivateDialog: (() => void) | null = null;

// 注册打开激活对话框的函数
export const registerActivateDialog = (fn: () => void) => {
  openActivateDialog = fn;
};

// 响应拦截器
api.interceptors.response.use(
  <T = any>(response: any): T => {
    return response.data as T;
  },
  (error: AxiosError<ErrorResponse>) => {
    const errorResponse = error.response?.data;
    const errorMessage = errorResponse?.error || error.message || '请求失败';
    const errorCode = errorResponse?.error_code;
    const errorType = errorResponse?.error_type;
    const statusCode = error.response?.status;
    
    // 对于长时间运行的请求，不自动显示错误提示
    if (error.config?.timeout && error.config.timeout > 60000) {
      return Promise.reject(error);
    }
    
    // 处理403错误（注册码相关限制）
    if (statusCode === 403 && errorType === 'license') {
      // 显示警告级别的提示
      message.warning(errorMessage, 5); // 显示5秒
      
      // 如果是未激活或过期，自动打开激活对话框
      if (errorCode === 'LICENSE_NOT_ACTIVATED' || errorCode === 'LICENSE_EXPIRED') {
        // 延迟打开，确保用户能看到提示消息
        setTimeout(() => {
          if (openActivateDialog) {
            openActivateDialog();
          }
        }, 500);
      }
      
      // 如果是任务数量限制，显示更详细的提示并引导用户查看套餐
      if (errorCode === 'TASK_LIMIT_REACHED') {
        Modal.warning({
          title: '任务数量限制',
          content: errorMessage,
          okText: '查看套餐',
          onOk: () => {
            // 触发打开套餐信息卡片的事件
            const event = new CustomEvent('openLicenseCard');
            window.dispatchEvent(event);
          }
        });
      }
    } 
    // 其他错误正常显示
    else {
      message.error(errorMessage);
    }
    
    return Promise.reject(error);
  }
);
```

#### 4.3.2 在组件中注册激活对话框

在应用初始化时（如 `App.tsx` 或主布局组件中）：

```tsx
import { useEffect } from 'react';
import { registerActivateDialog } from '@/services/api';
import { LicenseActivateDialog } from '@/components/LicenseActivateDialog';

const App = () => {
  const [activateDialogOpen, setActivateDialogOpen] = useState(false);
  
  useEffect(() => {
    // 注册打开激活对话框的函数
    registerActivateDialog(() => {
      setActivateDialogOpen(true);
    });
    
    // 监听打开套餐卡片的事件
    const handleOpenLicenseCard = () => {
      setLicenseCardVisible(true);
    };
    window.addEventListener('openLicenseCard', handleOpenLicenseCard);
    
    return () => {
      window.removeEventListener('openLicenseCard', handleOpenLicenseCard);
    };
  }, []);
  
  // ...
};
```

### 4.4 任务创建时的错误处理

在 `CreateTaskForm.tsx` 中，错误已经被 store 处理，但我们可以改进错误提示：

```tsx
// frontend/src/components/TaskForm/CreateTaskForm.tsx

const handleSubmit = async (values: any) => {
  setLoading(true);
  try {
    const data: TaskCreateRequest = { /* ... */ };
    await createTask(data);
    form.resetFields();
    onCancel();
    message.success('任务创建成功');
  } catch (error: any) {
    // 错误已在 api 拦截器中处理并显示
    // 但如果是注册码错误，不需要额外处理
    // 其他错误可以在这里添加特定处理
    const errorCode = error.response?.data?.error_code;
    if (errorCode === 'LICENSE_NOT_ACTIVATED' || errorCode === 'LICENSE_EXPIRED') {
      // 错误已自动打开激活对话框，这里不需要额外处理
      // 可以选择关闭创建任务对话框
      // onCancel();
    }
  } finally {
    setLoading(false);
  }
};
```

### 4.5 错误提示的展示层级

1. **普通错误**：使用 `message.error()` 在右上角显示（默认3秒）
2. **注册码未激活/过期**：使用 `message.warning()` 显示警告（5秒）+ 自动打开激活对话框
3. **任务数量限制**：使用 `Modal.warning()` 显示对话框，提供"查看套餐"按钮
4. **长时间运行的请求**：不在拦截器中显示，由调用方处理

### 4.6 错误消息模板

为了提供友好的错误提示，后端错误消息应包含：
- **问题描述**：清晰说明问题是什么
- **当前状态**：如"当前任务数：5"
- **限制信息**：如"最大任务数：100，剩余可用：95"
- **解决建议**：如"请先激活注册码"、"请重新激活注册码"

示例错误消息：
- ✅ 好的：`已达到最大任务数量限制（100），无法创建新任务。当前任务数：100，剩余可用：0`
- ❌ 不好的：`任务数量限制`

## 五、API 接口设计

### 5.1 获取激活状态

**接口**：`GET /api/v1/license/status`

**错误响应**（未激活）：
```json
{
  "success": false,
  "error": "产品未激活",
  "activated": false,
  "expired": false,
  "config": null
}
```

**响应**：
```json
{
  "success": true,
  "activated": true,
  "expired": false,
  "config": {
    "end_time": "2024-12-31T23:59:59",
    "task_num": 100,
    "is_free": false,
    "price": 100
  },
  "remaining_tasks": 95,
  "current_tasks": 5
}
```

### 4.2 激活注册码

**接口**：`POST /api/v1/license/activate`

**请求体**：
```json
{
  "license_code": "your_license_code_here"
}
```

**响应**：
```json
{
  "success": true,
  "message": "激活成功",
  "config": {
    "end_time": "2024-12-31T23:59:59",
    "task_num": 100,
    "is_free": false,
    "price": 100
  }
}
```

**错误响应**（注册码无效）：
```json
{
  "success": false,
  "error": "注册码无效或已过期",
  "error_code": "LICENSE_INVALID",
  "error_type": "license"
}
```

**错误响应**（网络错误）：
```json
{
  "success": false,
  "error": "无法连接到注册机服务，请检查网络连接",
  "error_code": "REGISTRY_SERVICE_UNAVAILABLE",
  "error_type": "system"
}
```

## 六、使用限制逻辑

### 6.1 免费试用版限制（未激活用户）

#### 6.1.1 任务数量限制
- **最大任务数**：1 个
- **检查逻辑**：在创建任务时检查 `当前任务数 < 1`
- **错误提示**：`免费试用版最多只能创建 1 个任务。请激活产品以创建更多任务。`
- **错误处理**：不弹出激活对话框，只显示友好提示

#### 6.1.2 执行间隔限制
- **固定间隔**：2 小时（7200 秒）
- **检查逻辑**：
  - 前端：禁用间隔滑块/输入框，固定显示 2 小时
  - 后端：创建任务时强制设置为 7200 秒，忽略用户输入
- **提示信息**：`免费试用版执行间隔固定为2小时（7200秒），激活后可自定义`

#### 6.1.3 立即执行限制
- **限制**：不允许立即执行任务
- **检查逻辑**：在立即执行接口中检查激活状态
- **错误提示**：`免费试用版不支持立即执行功能，请激活产品以使用此功能。`
- **UI表现**：任务列表中的"立即执行"按钮禁用，显示提示

### 6.2 已激活用户限制

#### 6.2.1 任务数量限制
- **最大任务数**：基于配置的 `task_num`
- **检查逻辑**：在创建任务时检查 `当前任务数 < task_num`
- **错误提示**：`已达到最大任务数量限制（{max_tasks}），无法创建新任务。当前任务数：{current_tasks}，剩余可用：{remaining}`
- **错误处理**：显示模态对话框，提供"查看套餐"按钮

#### 6.2.2 执行间隔限制
- **允许范围**：15 分钟（900 秒）- 3 小时（10800 秒）
- **检查逻辑**：创建任务时验证间隔是否在范围内
- **错误提示**：`执行间隔必须在900秒（15分钟）到10800秒（3小时）之间`

#### 6.2.3 过期检查
- **检查时间**：服务启动时、创建任务时、执行任务时
- **检查逻辑**：比较当前时间与 `end_time`
- **错误提示**：`产品已过期，过期时间：{end_time}。请重新激活注册码`
- **错误处理**：显示警告提示，自动打开激活对话框

### 6.3 限制检查流程图

```
用户操作（创建任务/执行任务）
    ↓
检查激活状态
    ↓
┌─────────────────┬─────────────────┐
│   未激活（免费试用）  │    已激活       │
├─────────────────┼─────────────────┤
│ 1. 任务数 < 1?   │ 1. 是否过期?      │
│ 2. 间隔=7200?   │ 2. 任务数 < max? │
│ 3. 禁用立即执行   │ 3. 间隔在范围?    │
└─────────────────┴─────────────────┘
    ↓                      ↓
友好提示             正常执行或错误提示
（不弹出激活对话框）        （可能弹出激活对话框）
```

## 七、开发步骤

### 阶段一：后端核心功能
1. ✅ 创建 `LicenseManager` 类
2. ✅ 实现注册码验证（调用注册机服务）
3. ✅ 实现配置加密存储和读取
4. ✅ 实现激活状态检查
5. ✅ 创建注册码路由接口

### 阶段二：后端集成
1. ✅ 在服务启动时验证激活状态
2. ✅ 在任务创建接口中添加限制检查
3. ✅ 测试各种限制场景

### 阶段三：前端UI
1. ✅ 修改侧边栏按钮
2. ✅ 创建套餐信息卡片组件
3. ✅ 创建激活码激活对话框
4. ✅ 创建注册码服务
5. ✅ 集成到主界面

### 阶段四：文档和测试
1. ✅ 创建激活码购买文档
2. ✅ 测试完整流程
3. ✅ 修复问题

## 八、注意事项

1. **安全性**
   - 加密密钥不要硬编码，使用环境变量或安全的密钥派生方式
   - 配置文件权限设置为 600
   - 注册码不要在前端日志中输出

2. **错误处理**
   - 注册机服务不可用时的处理
   - 配置文件损坏时的处理
   - 网络请求失败时的处理

3. **用户体验**
   - 激活失败时给出明确的错误提示
   - 限制达到时给出友好的提示信息
   - 激活成功后自动刷新状态

4. **兼容性**
   - 考虑已有用户的数据迁移（如果之前没有激活限制）
   - 配置文件格式版本管理

## 九、依赖项

### 后端
- `cryptography` - 用于加密配置文件
- `httpx` 或 `requests` - 用于调用注册机服务

### 前端
- 无需新增依赖，使用现有的 Ant Design 组件

## 十、测试场景

1. **激活流程**
   - 未激活状态下激活成功
   - 无效注册码激活失败
   - 已激活状态下重新激活

2. **限制检查**
   - 任务数量达到上限时无法创建
   - 过期后无法创建任务
   - 未激活时无法创建任务

3. **配置读取**
   - 服务启动时正确读取配置
   - 配置文件不存在时的处理
   - 配置文件损坏时的处理

4. **前端交互**
   - 套餐信息卡片显示正确
   - 激活对话框正常工作
   - 激活后状态自动更新
