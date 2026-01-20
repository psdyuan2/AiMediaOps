# AIMediaOps 前端架构设计文档

## 一、架构概述

采用**前后端分离架构**，使用现代前端技术栈构建专业、稳定、易维护的 Web 应用。

### 1.1 架构优势

- ✅ **前后端独立开发**：前后端可以并行开发，提高效率
- ✅ **技术栈现代化**：使用 React + TypeScript + Ant Design
- ✅ **代码质量高**：TypeScript 提供类型安全，组件化开发
- ✅ **UI 专业**：Ant Design 提供企业级组件，UI 更专业
- ✅ **性能优化**：代码分割、懒加载、虚拟滚动等
- ✅ **易于维护**：代码结构清晰，组件复用性高
- ✅ **易于扩展**：模块化设计，易于添加新功能

### 1.2 技术选型

#### 核心框架
- **React 18+**：主流前端框架，生态丰富
- **TypeScript**：类型安全，提升代码质量
- **Vite**：快速构建工具，开发体验好

#### UI 组件库
- **Ant Design (antd)**：企业级 UI 设计语言
  - 组件丰富（60+ 组件）
  - 文档完善，中文支持好
  - 主题定制灵活
  - 适合后台管理系统

#### 状态管理
- **Zustand**：轻量级状态管理
  - API 简洁，学习成本低
  - 性能好，体积小
  - 适合中小型项目

#### 路由
- **React Router v6**：React 官方推荐路由库

#### HTTP 客户端
- **Axios**：功能强大的 HTTP 客户端
  - 支持拦截器
  - 自动 JSON 转换
  - 请求/响应拦截

#### 工具库
- **dayjs**：日期处理（轻量级 moment.js 替代）
- **lodash-es**：工具函数库（按需引入）

## 二、项目结构

```
frontend/
├── public/                 # 静态资源
│   ├── favicon.ico
│   └── ...
├── src/
│   ├── components/        # 公共组件
│   │   ├── Layout/        # 布局组件
│   │   │   ├── MainLayout.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── index.ts
│   │   ├── TaskCard/      # 任务卡片
│   │   │   ├── TaskCard.tsx
│   │   │   ├── TaskCardHeader.tsx
│   │   │   ├── TaskCardContent.tsx
│   │   │   └── index.ts
│   │   ├── DispatcherControl/ # 调度器控制
│   │   │   ├── DispatcherControl.tsx
│   │   │   └── index.ts
│   │   ├── TaskList/      # 任务列表
│   │   │   ├── TaskList.tsx
│   │   │   └── index.ts
│   │   ├── TaskForm/      # 任务表单
│   │   │   ├── CreateTaskForm.tsx
│   │   │   ├── EditTaskForm.tsx
│   │   │   └── index.ts
│   │   ├── LoginDialog/   # 登录对话框
│   │   │   ├── LoginDialog.tsx
│   │   │   └── index.ts
│   │   ├── LogViewer/     # 日志查看器
│   │   │   ├── LogViewer.tsx
│   │   │   └── index.ts
│   │   └── ResourceManager/ # 资源管理
│   │       ├── ResourceManager.tsx
│   │       └── index.ts
│   ├── pages/             # 页面组件
│   │   ├── Dashboard/     # 主页面
│   │   │   ├── Dashboard.tsx
│   │   │   └── index.ts
│   │   └── ...
│   ├── services/          # API 服务
│   │   ├── api.ts         # API 配置
│   │   ├── taskService.ts # 任务相关 API
│   │   ├── dispatcherService.ts # 调度器相关 API
│   │   └── types.ts       # API 类型定义
│   ├── store/             # 状态管理
│   │   ├── taskStore.ts   # 任务状态
│   │   ├── dispatcherStore.ts # 调度器状态
│   │   └── index.ts
│   ├── hooks/             # 自定义 Hooks
│   │   ├── useTask.ts
│   │   ├── useDispatcher.ts
│   │   └── ...
│   ├── utils/             # 工具函数
│   │   ├── format.ts      # 格式化工具
│   │   ├── request.ts     # 请求工具
│   │   └── constants.ts   # 常量
│   ├── types/             # TypeScript 类型定义
│   │   ├── task.ts
│   │   ├── dispatcher.ts
│   │   └── api.ts
│   ├── styles/            # 样式文件
│   │   ├── global.css
│   │   └── antd.less      # Ant Design 主题定制
│   ├── App.tsx            # 根组件
│   ├── main.tsx           # 入口文件
│   └── vite-env.d.ts      # Vite 类型声明
├── .env.development       # 开发环境配置
├── .env.production        # 生产环境配置
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 三、核心组件设计

### 3.1 布局组件

```tsx
// src/components/Layout/MainLayout.tsx
import { Layout } from 'antd';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Outlet } from 'react-router-dom';

const { Content } = Layout;

export const MainLayout: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header />
      <Layout>
        <Sidebar />
        <Content style={{ padding: '24px', background: '#f0f2f5' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};
```

### 3.2 任务卡片组件

```tsx
// src/components/TaskCard/TaskCard.tsx
import { Card, Badge, Button, Space, Collapse, Tag } from 'antd';
import { EditOutlined, DeleteOutlined, LoginOutlined } from '@ant-design/icons';
import { Task } from '@/types/task';

interface TaskCardProps {
  task: Task;
  onEdit: (taskId: string) => void;
  onDelete: (taskId: string) => void;
  onLogin: (taskId: string) => void;
  // ... 其他操作
}

export const TaskCard: React.FC<TaskCardProps> = ({ task, ... }) => {
  const getStatusColor = (status: string) => {
    const colors = {
      pending: 'default',
      running: 'processing',
      paused: 'warning',
      completed: 'success',
      error: 'error',
    };
    return colors[status] || 'default';
  };

  return (
    <Card
      title={
        <Space>
          <span>{task.account_name || task.account_id}</span>
          {task.login_status !== null && (
            <Tag color={task.login_status ? 'green' : 'red'}>
              {task.login_status ? '✓ 已登录' : '✗ 未登录'}
            </Tag>
          )}
        </Space>
      }
      extra={
        <Space>
          <Button icon={<EditOutlined />} onClick={() => onEdit(task.id)} />
          <Button icon={<DeleteOutlined />} danger onClick={() => onDelete(task.id)} />
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Badge status={getStatusColor(task.status)} text={task.status} />
        <div>下次执行: {formatDateTime(task.next_execution_time)}</div>
        <div>执行轮次: {task.round_num || 0}</div>
        
        <Collapse>
          <Collapse.Panel header="操作" key="1">
            <Space wrap>
              <Button type="primary" onClick={() => onExecute(task.id)}>
                立即执行
              </Button>
              <Button onClick={() => onPause(task.id)}>暂停</Button>
              <Button icon={<LoginOutlined />} onClick={() => onLogin(task.id)}>
                登录
              </Button>
              <Button onClick={() => onViewLogs(task.id)}>日志</Button>
              <Button onClick={() => onViewResources(task.id)}>资源</Button>
            </Space>
          </Collapse.Panel>
        </Collapse>
      </Space>
    </Card>
  );
};
```

### 3.3 调度器控制组件

```tsx
// src/components/DispatcherControl/DispatcherControl.tsx
import { Card, Button, Statistic, Row, Col, Space } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { useDispatcherStore } from '@/store/dispatcherStore';

export const DispatcherControl: React.FC = () => {
  const { status, totalTasks, runningTasks, startDispatcher, stopDispatcher, refreshStatus } = useDispatcherStore();

  return (
    <Card>
      <Row gutter={16} align="middle">
        <Col>
          <Space>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={startDispatcher}
              disabled={status.is_running}
            >
              启动调度器
            </Button>
            <Button
              danger
              icon={<PauseCircleOutlined />}
              onClick={stopDispatcher}
              disabled={!status.is_running}
            >
              停止调度器
            </Button>
            <Button icon={<ReloadOutlined />} onClick={refreshStatus}>
              刷新状态
            </Button>
          </Space>
        </Col>
        <Col flex="auto" />
        <Col>
          <Space size="large">
            <Statistic title="总任务" value={totalTasks} />
            <Statistic title="运行中" value={runningTasks} />
            <Statistic
              title="状态"
              value={status.is_running ? '运行中' : '已停止'}
              valueStyle={{ color: status.is_running ? '#3f8600' : '#cf1322' }}
            />
          </Space>
        </Col>
      </Row>
    </Card>
  );
};
```

## 四、API 服务层

### 4.1 API 配置

```typescript
// src/services/api.ts
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { message } from 'antd';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data;
  },
  (error) => {
    // 统一错误处理
    const errorMessage = error.response?.data?.detail || error.message || '请求失败';
    message.error(errorMessage);
    return Promise.reject(error);
  }
);

export default api;
```

### 4.2 任务服务

```typescript
// src/services/taskService.ts
import api from './api';
import { Task, TaskListResponse, TaskCreateRequest, TaskUpdateRequest } from '@/types/task';

export const taskService = {
  // 获取任务列表
  getTasks: (params?: { account_id?: string; status?: string; limit?: number; offset?: number }) =>
    api.get<TaskListResponse>('/tasks', { params }),

  // 获取任务详情
  getTask: (taskId: string) =>
    api.get<Task>(`/tasks/${taskId}`),

  // 创建任务
  createTask: (data: TaskCreateRequest) =>
    api.post<Task>('/tasks', data),

  // 更新任务
  updateTask: (taskId: string, data: TaskUpdateRequest) =>
    api.patch<Task>(`/tasks/${taskId}`, data),

  // 删除任务
  deleteTask: (taskId: string) =>
    api.delete(`/tasks/${taskId}`),

  // 暂停任务
  pauseTask: (taskId: string) =>
    api.post(`/tasks/${taskId}/pause`),

  // 恢复任务
  resumeTask: (taskId: string) =>
    api.post(`/tasks/${taskId}/resume`),

  // 立即执行
  executeTask: (taskId: string) =>
    api.post(`/tasks/${taskId}/execute`, {}, { timeout: 1800000 }), // 30 分钟超时

  // 获取任务日志
  getTaskLogs: (taskId: string, params?: { since?: string; level?: string; limit?: number }) =>
    api.get(`/tasks/${taskId}/logs`, { params }),

  // 获取登录二维码
  getLoginQrcode: (taskId: string) =>
    api.get(`/tasks/${taskId}/login/qrcode`),

  // 检查登录状态
  checkLoginStatus: (taskId: string) =>
    api.get(`/tasks/${taskId}/login/status`),

  // 确认登录
  confirmLogin: (taskId: string) =>
    api.post(`/tasks/${taskId}/login/confirm`),

  // 获取任务图片列表
  getTaskImages: (taskId: string) =>
    api.get(`/tasks/${taskId}/resources/images`),

  // 获取知识库文件
  getSourceFile: (taskId: string) =>
    api.get(`/tasks/${taskId}/resources/source`),

  // 更新知识库文件
  updateSourceFile: (taskId: string, content: string) =>
    api.put(`/tasks/${taskId}/resources/source`, { content }),
};
```

## 五、状态管理

### 5.1 任务状态管理

```typescript
// src/store/taskStore.ts
import { create } from 'zustand';
import { taskService } from '@/services/taskService';
import { Task, TaskCreateRequest, TaskUpdateRequest } from '@/types/task';

interface TaskStore {
  tasks: Task[];
  loading: boolean;
  error: string | null;
  selectedTask: Task | null;

  // Actions
  fetchTasks: () => Promise<void>;
  createTask: (data: TaskCreateRequest) => Promise<void>;
  updateTask: (taskId: string, data: TaskUpdateRequest) => Promise<void>;
  deleteTask: (taskId: string) => Promise<void>;
  pauseTask: (taskId: string) => Promise<void>;
  resumeTask: (taskId: string) => Promise<void>;
  executeTask: (taskId: string) => Promise<void>;
  selectTask: (task: Task | null) => void;
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: [],
  loading: false,
  error: null,
  selectedTask: null,

  fetchTasks: async () => {
    set({ loading: true, error: null });
    try {
      const response = await taskService.getTasks({ limit: 1000 });
      set({ tasks: response.tasks, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createTask: async (data) => {
    try {
      await taskService.createTask(data);
      await get().fetchTasks(); // 刷新列表
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  updateTask: async (taskId, data) => {
    try {
      await taskService.updateTask(taskId, data);
      await get().fetchTasks(); // 刷新列表
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  deleteTask: async (taskId) => {
    try {
      await taskService.deleteTask(taskId);
      await get().fetchTasks(); // 刷新列表
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  pauseTask: async (taskId) => {
    try {
      await taskService.pauseTask(taskId);
      await get().fetchTasks();
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  resumeTask: async (taskId) => {
    try {
      await taskService.resumeTask(taskId);
      await get().fetchTasks();
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  executeTask: async (taskId) => {
    try {
      await taskService.executeTask(taskId);
      await get().fetchTasks();
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  selectTask: (task) => {
    set({ selectedTask: task });
  },
}));
```

### 5.2 调度器状态管理

```typescript
// src/store/dispatcherStore.ts
import { create } from 'zustand';
import { dispatcherService } from '@/services/dispatcherService';
import { DispatcherStatus } from '@/types/dispatcher';

interface DispatcherStore {
  status: DispatcherStatus | null;
  loading: boolean;
  error: string | null;

  fetchStatus: () => Promise<void>;
  startDispatcher: () => Promise<void>;
  stopDispatcher: () => Promise<void>;
}

export const useDispatcherStore = create<DispatcherStore>((set, get) => ({
  status: null,
  loading: false,
  error: null,

  fetchStatus: async () => {
    set({ loading: true, error: null });
    try {
      const status = await dispatcherService.getStatus();
      set({ status, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  startDispatcher: async () => {
    try {
      await dispatcherService.start();
      await get().fetchStatus();
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  stopDispatcher: async () => {
    try {
      await dispatcherService.stop();
      await get().fetchStatus();
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },
}));
```

## 六、类型定义

### 6.1 任务类型

```typescript
// src/types/task.ts
export interface Task {
  task_id: string;
  account_id: string;
  account_name: string;
  task_type: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'error';
  interval: number;
  valid_time_range: [number, number];
  task_end_time: string;
  last_execution_time: string | null;
  next_execution_time: string | null;
  created_at: string;
  updated_at: string;
  round_num: number | null;
  kwargs: Record<string, any>;
  login_status: boolean | null;
  login_status_checked_at: string | null;
}

export interface TaskCreateRequest {
  sys_type: string;
  task_type: string;
  xhs_account_id: string;
  xhs_account_name: string;
  user_query?: string;
  user_topic?: string;
  user_style?: string;
  user_target_audience?: string;
  task_end_time?: string;
  interval?: number;
  valid_time_range?: [number, number];
}

export interface TaskUpdateRequest {
  user_query?: string;
  user_topic?: string;
  user_style?: string;
  user_target_audience?: string;
  task_end_time?: string;
  interval?: number;
  valid_time_range?: [number, number];
}

export interface TaskListResponse {
  total: number;
  tasks: Task[];
}
```

## 七、开发配置

### 7.1 Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### 7.2 TypeScript 配置

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### 7.3 环境变量

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

```bash
# .env.production
VITE_API_BASE_URL=/api/v1
```

## 八、后端 CORS 配置

需要在 FastAPI 中添加 CORS 支持：

```python
# app/api/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Vite 默认端口
        "http://localhost:5173",  # Vite 备用端口
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 九、开发流程

### 9.1 初始化项目

```bash
# 1. 创建项目
npm create vite@latest frontend -- --template react-ts
cd frontend

# 2. 安装依赖
npm install antd axios zustand react-router-dom dayjs
npm install -D @types/node

# 3. 启动开发服务器
npm run dev
```

### 9.2 开发步骤

1. **搭建基础结构**
   - 创建项目结构
   - 配置路由
   - 配置 API 服务

2. **实现核心组件**
   - 布局组件
   - 任务卡片组件
   - 调度器控制组件

3. **实现功能页面**
   - 主页面（Dashboard）
   - 任务管理
   - 登录功能
   - 资源管理

4. **优化和测试**
   - UI 优化
   - 性能优化
   - 错误处理
   - 响应式适配

## 十、优势总结

### 10.1 技术优势

- ✅ **React 生态**：丰富的第三方库和工具
- ✅ **TypeScript**：类型安全，减少运行时错误
- ✅ **Ant Design**：专业的企业级 UI 组件
- ✅ **组件化**：代码复用性高，易于维护
- ✅ **性能优化**：代码分割、懒加载、虚拟滚动

### 10.2 开发优势

- ✅ **开发效率**：热更新、快速构建
- ✅ **代码质量**：TypeScript + ESLint + Prettier
- ✅ **团队协作**：前后端独立开发
- ✅ **易于测试**：组件可独立测试

### 10.3 维护优势

- ✅ **代码结构清晰**：模块化设计
- ✅ **易于扩展**：添加新功能简单
- ✅ **文档完善**：React、Ant Design 文档齐全
- ✅ **社区支持**：问题容易找到解决方案

---

**文档版本**：v1.0  
**创建时间**：2026-01-14
