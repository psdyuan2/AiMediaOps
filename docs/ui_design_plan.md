# AIMediaOps Web UI 设计方案

## 一、设计概述

基于 Figma 设计稿，结合当前产品功能，设计一个现代化的任务调度管理 Web 界面。

### 1.1 设计目标
- **现代化**：使用现代 UI 组件库，提升视觉体验
- **一致性**：保持与当前产品功能完全一致
- **易用性**：优化交互流程，提升用户体验
- **响应式**：支持不同屏幕尺寸
- **可维护性**：前后端分离，代码结构清晰，易于维护和扩展

### 1.2 架构方案：前后端分离

**采用前后端分离架构，优势：**
- ✅ 前后端独立开发和部署
- ✅ 使用现代前端框架（React/Vue），代码组织更清晰
- ✅ 使用专业组件库（Ant Design/Material UI），UI 更专业
- ✅ 更好的性能优化（代码分割、懒加载、虚拟滚动等）
- ✅ 更好的开发体验（热更新、TypeScript 支持、组件化开发）
- ✅ 前端代码更稳定，易于测试和维护

### 1.3 技术选型

#### 前端技术栈
- **框架**：React 18+（推荐）或 Vue 3（备选）
- **UI 组件库**：
  - **推荐：Ant Design (antd)** - 企业级 UI 设计语言，组件丰富，文档完善
  - **备选：Material UI (MUI)** - Google Material Design，组件质量高
- **状态管理**：
  - React: Zustand（轻量）或 Redux Toolkit（复杂场景）
  - Vue: Pinia
- **路由**：
  - React: React Router v6
  - Vue: Vue Router
- **HTTP 客户端**：Axios
- **构建工具**：Vite（推荐，快速）或 Create React App
- **TypeScript**：强烈推荐，提升代码质量和开发体验
- **样式方案**：
  - Ant Design 内置样式（推荐）
  - 或 Tailwind CSS + Ant Design（自定义主题）

#### 后端技术栈（保持不变）
- **框架**：FastAPI（当前）
- **API 格式**：RESTful API（当前）
- **CORS**：需要配置跨域支持

#### 项目结构
```
AiMediaOps/
├── backend/              # 后端（当前 app/ 目录）
│   ├── app/
│   └── ...
├── frontend/            # 前端（新建）
│   ├── src/
│   │   ├── components/  # 组件
│   │   ├── pages/      # 页面
│   │   ├── services/   # API 服务
│   │   ├── store/      # 状态管理
│   │   ├── utils/      # 工具函数
│   │   └── App.tsx     # 入口
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
└── docs/
```

## 二、页面结构分析

### 2.1 整体布局

```
┌─────────────────────────────────────────────────────────┐
│  顶部导航栏 (Top Navigation Bar)                        │
│  [Logo] 首页 | 员工部署 | 帮助文档 | ... [Sign in]      │
├──────────┬──────────────────────────────────────────────┤
│          │  ┌────────────────────────────────────────┐  │
│ 左侧     │  │  调度器标签页 (Scheduler Tabs)        │  │
│ 设置面板 │  │  [小红书运营] [其他调度器...]         │  │
│          │  ├────────────────────────────────────────┤  │
│ (Setting)│  │  调度器详情 (Scheduler Details)       │  │
│          │  │  名称、描述、运行日志                   │  │
│ - Interval│  ├────────────────────────────────────────┤  │
│ - End Time│  │  任务列表 (Task List)                  │  │
│          │  │  [任务卡片1] [任务卡片2] ...           │  │
│ [新建员工]│  └────────────────────────────────────────┘  │
│ [查看套餐]│                                               │
└──────────┴──────────────────────────────────────────────┘
```

### 2.2 组件映射关系

| Figma 设计元素 | 当前功能 | 实现方案 |
|---------------|---------|---------|
| 顶部导航栏 | 当前无 | 新增：首页、帮助文档等导航 |
| 左侧设置面板 | 当前无 | 新增：调度器/任务参数设置区域 |
| 调度器标签页 | 当前无 | 新增：多调度器切换（当前为单调度器） |
| 调度器详情 | 当前无 | 新增：调度器名称、描述、运行日志 |
| 任务列表卡片 | 当前表格形式 | 改为卡片式，支持展开/收起 |
| 任务操作按钮 | 当前在表格中 | 集成到任务卡片中 |

## 三、功能映射与设计

### 3.1 顶部导航栏

**设计元素**：
- Logo（左侧）
- 导航链接：首页、员工部署、帮助文档、Resources、Pricing、Contact （一些暂时没有的资源可以先留一个tab）
- 右侧：Sign in、Register

**当前功能对应**：
- 当前无顶部导航，所有功能在单页面中
- **建议**：保留单页面设计，顶部导航可简化为：
  - Logo + 标题 "AIMediaOps"
  - 帮助文档链接
  - 用户信息/设置（如果未来需要）
（logo图可以先空着）
**实现方案**：
```html
<nav class="bg-white border-b border-gray-200">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <div class="flex items-center">
        <Logo />
        <span class="ml-2 text-xl font-semibold">AIMediaOps</span>
      </div>
      <div class="flex items-center space-x-4">
        <a href="#help">帮助文档</a>
      </div>
    </div>
  </div>
</nav>
```

### 3.2 左侧设置面板

**设计元素**：
- Interval 滑块
- End Time 下拉菜单
- "新建员工" 按钮
- "查看当前套餐" 按钮

**当前功能对应**：
- **Interval**：对应任务的 `interval` 参数（执行间隔）
- **End Time**：对应任务的 `task_end_time` 参数
- **新建员工**：对应"创建任务"功能
- **查看当前套餐**：当前无此功能，可暂时隐藏或作为占位

**实现方案**：
```html
<aside class="w-64 bg-gray-50 border-r border-gray-200 p-6">
  <h2 class="text-lg font-semibold mb-4">设置</h2>
  
  <!-- Interval 滑块 -->
  <div class="mb-6">
    <label class="block text-sm font-medium text-gray-700 mb-2">
      执行间隔 (秒)
    </label>
    <input type="range" min="60" max="86400" step="60" 
           class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
    <div class="flex justify-between text-xs text-gray-500 mt-1">
      <span>1分钟</span>
      <span>24小时</span>
    </div>
  </div>
  
  <!-- End Time 选择器 -->
  <div class="mb-6">
    <label class="block text-sm font-medium text-gray-700 mb-2">
      结束时间
    </label>
    <input type="date" class="w-full px-3 py-2 border border-gray-300 rounded-md" />
  </div>
  
  <!-- 操作按钮 -->
  <button class="w-full bg-gray-800 text-white py-2 px-4 rounded-md mb-2">
    新建任务
  </button>
  <button class="w-full bg-gray-200 text-gray-800 py-2 px-4 rounded-md">
    查看当前套餐
  </button>
</aside>
```

**交互逻辑**：
- 当选中任务时，显示该任务的参数（可编辑）
- 当未选中任务时，显示默认值（用于新建任务）
- 参数修改后，实时保存到后端

### 3.3 调度器标签页

**设计元素**：
- 当前查看的调度器：显示完整信息（头像、名称、账号数、运行状态）
- 其他调度器：显示缩略信息（头像、名称缩写）

**当前功能对应**：
- 当前系统为单调度器设计
- **建议**：暂时实现为单调度器视图，但保留扩展性

**实现方案**：
```html
<div class="flex space-x-2 border-b border-gray-200">
  <!-- 当前调度器（展开） -->
  <div class="px-4 py-3 bg-white border-b-2 border-blue-500 flex items-center space-x-3">
    <img src="avatar.png" class="w-8 h-8 rounded-full" />
    <div>
      <div class="font-medium">小红书运营</div>
      <div class="text-sm text-gray-500">5个账号</div>
    </div>
    <span class="ml-auto">
      <PlayIcon class="w-5 h-5 text-green-500" />
    </span>
  </div>
  
  <!-- 其他调度器（缩略） -->
  <div class="px-3 py-3 flex items-center space-x-2">
    <img src="avatar.png" class="w-6 h-6 rounded-full" />
    <span class="text-sm">运营...</span>
  </div>
</div>
```

### 3.4 调度器详情区域

**设计元素**：
- 调度器名称和描述
- 运行任务日志（实时显示）

**当前功能对应**：
- 调度器名称：可显示为 "任务调度器" 或自定义名称
- 调度器描述：可显示调度器状态信息
- 运行日志：对应当前任务的实时日志

**实现方案**：
```html
<div class="p-6">
  <!-- 调度器信息 -->
  <div class="mb-6">
    <h1 class="text-2xl font-bold mb-2">负责小红书的运营</h1>
    <p class="text-gray-600">
      自动化管理小红书账号，定时发布内容，提升运营效率
    </p>
  </div>
  
  <!-- 运行日志 -->
  <div class="bg-gray-100 rounded-lg p-4 mb-6">
    <div class="text-sm text-gray-600">
      <div class="mb-1">2025.1.10 log generate some awesome notes</div>
      <div class="mb-1">2025.1.10 log generate some awesome notes</div>
    </div>
  </div>
</div>
```

### 3.5 任务列表（卡片式）

**设计元素**：
- 任务卡片，包含：
  - 任务名称（账号名称）
  - 账号信息
  - 编辑/删除图标
  - 展开/收起箭头

**当前功能对应**：
- 当前为表格形式，需要改为卡片式
- 任务操作：编辑、删除、暂停、恢复、立即执行、登录、资源、日志

**实现方案**：
```html
<div class="space-y-4">
  <!-- 任务卡片 -->
  <div class="bg-white border border-gray-200 rounded-lg p-4">
    <!-- 卡片头部（始终显示） -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div>
          <div class="font-medium">花语堂</div>
          <div class="text-sm text-gray-500">
            账号名称: XXXX | 账号ID: 花语堂
          </div>
        </div>
        <!-- 登录状态标识 -->
        <span class="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
          ✓ 已登录
        </span>
      </div>
      
      <div class="flex items-center space-x-2">
        <!-- 操作按钮 -->
        <button class="p-2 hover:bg-gray-100 rounded">
          <EditIcon class="w-4 h-4" />
        </button>
        <button class="p-2 hover:bg-gray-100 rounded">
          <TrashIcon class="w-4 h-4" />
        </button>
        <!-- 展开/收起 -->
        <button class="p-2 hover:bg-gray-100 rounded">
          <ChevronDownIcon class="w-4 h-4" />
        </button>
      </div>
    </div>
    
    <!-- 卡片内容（可展开） -->
    <div class="mt-4 pt-4 border-t border-gray-200 hidden">
      <!-- 任务状态 -->
      <div class="mb-4">
        <span class="px-2 py-1 rounded text-xs bg-blue-100 text-blue-800">
          等待执行
        </span>
      </div>
      
      <!-- 任务信息 -->
      <div class="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span class="text-gray-500">下次执行:</span>
          <span class="ml-2">2026-01-15 10:00</span>
        </div>
        <div>
          <span class="text-gray-500">执行轮次:</span>
          <span class="ml-2">5</span>
        </div>
      </div>
      
      <!-- 操作按钮组 -->
      <div class="mt-4 flex flex-wrap gap-2">
        <button class="px-3 py-1 bg-green-600 text-white rounded text-xs">
          立即执行
        </button>
        <button class="px-3 py-1 bg-yellow-600 text-white rounded text-xs">
          暂停
        </button>
        <button class="px-3 py-1 bg-teal-600 text-white rounded text-xs">
          登录
        </button>
        <button class="px-3 py-1 bg-amber-600 text-white rounded text-xs">
          资源
        </button>
        <button class="px-3 py-1 bg-purple-600 text-white rounded text-xs">
          日志
        </button>
      </div>
    </div>
  </div>
</div>
```

## 四、交互设计

### 4.1 任务卡片交互

1. **展开/收起**：
   - 点击右侧箭头，展开/收起任务详情
   - 展开时显示：状态、下次执行时间、执行轮次、操作按钮

2. **快速操作**：
   - 卡片头部始终显示：编辑、删除图标
   - 展开后显示完整操作按钮组

3. **状态标识**：
   - 登录状态：绿色（已登录）/ 红色（未登录）
   - 任务状态：不同颜色徽章（等待、运行中、已暂停等）

### 4.2 左侧设置面板交互

1. **上下文感知**：
   - 未选中任务：显示默认值，用于新建任务
   - 选中任务：显示该任务的参数，可编辑

2. **实时保存**：
   - 修改参数后，自动保存到后端
   - 显示保存状态（成功/失败）

3. **新建任务**：
   - 点击"新建任务"按钮，打开创建任务对话框
   - 使用左侧面板的参数作为默认值

### 4.3 调度器详情交互

1. **运行日志**：
   - 实时显示当前运行任务的日志
   - 支持自动滚动到底部
   - 支持清空日志

2. **调度器状态**：
   - 显示调度器运行状态（运行中/已停止）
   - 显示任务统计（总数、运行中、等待中等）

## 五、响应式设计

### 5.1 断点设计

- **移动端** (< 768px)：
  - 左侧面板收起为抽屉式
  - 任务卡片全宽显示
  - 顶部导航简化

- **平板** (768px - 1024px)：
  - 左侧面板可折叠
  - 任务卡片两列显示

- **桌面** (> 1024px)：
  - 完整布局
  - 左侧面板固定宽度
  - 任务卡片多列显示（可选）

### 5.2 适配策略

```css
/* 移动端 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: -100%;
    transition: left 0.3s;
  }
  .sidebar.open {
    left: 0;
  }
}

/* 桌面端 */
@media (min-width: 1024px) {
  .sidebar {
    position: relative;
    width: 256px;
  }
}
```

## 六、UI 组件库选择

### 6.1 推荐方案：shadcn/ui + Tailwind CSS

**优势**：
- 基于 Tailwind CSS，与当前技术栈一致
- 高度可定制，不依赖特定框架
- 组件质量高，设计现代
- 支持暗色模式（可选）

**核心组件**：
- Button、Input、Select、Slider
- Card、Dialog、Dropdown Menu
- Badge、Tooltip、Toast

### 6.2 备选方案：Headless UI + Tailwind CSS

**优势**：
- 完全无样式，完全自定义
- 无障碍支持好
- 与 Tailwind CSS 完美集成

## 七、实现优先级

### Phase 1: 核心功能迁移（必须）
1. ✅ 任务列表改为卡片式
2. ✅ 任务操作按钮集成到卡片
3. ✅ 登录状态标识显示
4. ✅ 保持所有现有功能

### Phase 2: 新增功能（重要）
1. 左侧设置面板
2. 调度器详情区域
3. 运行日志实时显示

### Phase 3: 优化体验（可选）
1. 调度器标签页（多调度器支持）
2. 顶部导航栏
3. 响应式适配
4. 动画效果

## 八、技术实现细节

### 8.1 状态管理

- 使用原生 JavaScript（当前方案）
- 或考虑引入轻量级状态管理（如 Zustand，可选）

### 8.2 API 集成

- 保持现有 API 调用方式
- 使用 `fetch` 或 `axios`（如果引入）

### 8.3 实时更新

- 任务列表：定时刷新（当前 10 秒）
- 运行日志：WebSocket 或 Server-Sent Events（可选，未来优化）

## 九、设计疑问与建议

### 9.1 需要确认的问题

1. **调度器概念**：
   - 当前系统为单调度器，设计稿显示多调度器 
   - **建议**：Phase 1 先实现单调度器视图，保留扩展性 （可以）

2. **"员工部署"功能**：
   - 设计稿中有"员工部署"导航，当前系统无此功能
   - **建议**：暂时隐藏或作为占位 （这里员工其实就是指调度器，部署员工就是部署一个新的调度器。但是我认为员工这个名词容易引发歧义，还是将员工统一改成AI运营专家吧）

3. **"查看当前套餐"功能**：
   - 设计稿中有此按钮，当前系统无此功能
   - **建议**：暂时隐藏或作为占位 （先用按钮占位，后续开发好服务后再继续完善）

4. **左侧设置面板的作用域**：
   - 是全局设置还是任务级设置？
   - **建议**：任务级设置，选中任务时显示该任务的参数 （没错，显示的是选中任务的设置）

### 9.2 设计建议

1. **保持功能优先**：
   - 如果设计与当前功能冲突，以功能实现为准
   - 设计作为视觉优化，不影响功能逻辑

2. **渐进式实现**：
   - 先实现核心功能迁移
   - 再逐步添加新功能
   - 最后优化视觉和交互

3. **向后兼容**：
   - 保持 API 接口不变
   - 前端重构不影响后端逻辑

## 十、下一步行动

1. **确认设计方案**：与产品/设计确认设计细节
2. **技术选型确认**：确定 UI 组件库
3. **开发计划**：制定详细的开发计划和时间表
4. **开始实现**：按照优先级逐步实现

---

**文档版本**：v1.0  
**创建时间**：2026-01-14  
**最后更新**：2026-01-14
