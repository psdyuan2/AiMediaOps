# Web登录功能 - 开发方案设计

## 需求分析

1. **每次任务执行完 run_once，删除 xhs_mcp/cookies.json**
2. **任务执行前，通过 MCP 校验是否登录（非登录态）**
3. **如果未登录，获取二维码，在前端展示**
4. **用户扫码后点击确定**
5. **检查登录态，如果校验通过，展示登录成功**

## 技术方案设计

### 一、后端 API 层

#### 1. GET /tasks/{task_id}/login/qrcode
- **功能**：获取登录二维码（base64编码）
- **实现**：通过 `task_info.task_manager.agent` 获取二维码
- **返回**：
  ```json
  {
    "qrcode_base64": "iVBORw0KGgoAAAANS...",
    "qrcode_url": "data:image/png;base64,..."
  }
  ```

#### 2. GET /tasks/{task_id}/login/status
- **功能**：检查登录状态
- **实现**：通过 `task_info.task_manager.agent` 检查登录状态
- **返回**：
  ```json
  {
    "is_logged_in": true,
    "message": "已登录"
  }
  ```

#### 3. POST /tasks/{task_id}/login/confirm
- **功能**：确认登录（检查状态并返回结果）
- **实现**：调用 `check_login_status` 并返回结果
- **返回**：
  ```json
  {
    "success": true,
    "is_logged_in": true,
    "message": "登录成功"
  }
  ```

### 二、TaskManager 修改

#### 修改 _close_task() 方法
- **功能**：在任务执行完成后，删除 `xhs_mcp/cookies.json`
- **实现**：
  ```python
  def _close_task(self):
      # 1. 保留现有逻辑：将 cookies 复制回用户专属目录
      # 2. 新增：删除 xhs_mcp/cookies.json
      mcp_cookies_path = os.path.join(COOKIE_SOURCE_PATH, "cookies.json")
      if os.path.exists(mcp_cookies_path):
          os.remove(mcp_cookies_path)
          logger.info(f"已删除 MCP cookies: {mcp_cookies_path}")
  ```

### 三、前端 UI 层

#### 1. 登录对话框（loginDialog）
- **结构**：
  - 标题：小红书登录
  - 二维码图片区域
  - 状态提示文字
  - "确认登录"按钮
  - "取消"按钮

#### 2. JavaScript 函数
- `showLoginDialog(taskId)` - 显示登录对话框
- `loadLoginQrcode(taskId)` - 加载二维码
- `checkLoginStatus(taskId)` - 检查登录状态
- `confirmLogin(taskId)` - 确认登录
- `closeLoginDialog()` - 关闭登录对话框

#### 3. 登录流程触发
- **方案一（推荐）**：用户主动触发
  - 在任务列表中添加"登录"按钮
  - 点击后弹出登录对话框
- **方案二**：自动触发
  - 任务执行时，如果检测到未登录状态，自动弹出登录对话框
  - 需要前端轮询检查登录状态

### 四、关键实现细节

#### 1. Cookies 路径
- **MCP 服务使用的 cookies**：`xhs_mcp/cookies.json`
- **用户专属 cookies**：`app/data/task_data/{user_id}/cookies/cookies.json`
- **任务执行后**：删除 `xhs_mcp/cookies.json`，保留用户专属目录的 cookies

#### 2. Agent 使用
- 通过 `task_info.task_manager.agent` 访问 Agent 实例
- 确保 MCP 连接已建立（调用 `ensure_connected()`）
- 使用 `agent.mcp_client` 调用 MCP 工具

#### 3. 二维码格式
- MCP 返回 base64 编码的图片
- 前端使用 `<img src='data:image/png;base64,...'/>` 显示

#### 4. 登录流程
- 用户点击"登录"按钮
- 前端调用 API 获取二维码
- 显示二维码
- 用户扫码后，点击"确认登录"
- 前端调用 API 检查登录状态
- 如果登录成功，关闭对话框；如果失败，提示用户重试

## 代码修改清单

1. **app/api/models.py** - 添加登录相关响应模型
2. **app/api/routers/tasks.py** - 添加登录相关 API 端点
3. **app/manager/task_manager.py** - 修改 `_close_task()` 删除 cookies
4. **app/api/static/index.html** - 添加登录对话框和 JavaScript 函数

## 实现优先级

1. **高优先级**：后端 API + 前端 UI（用户主动触发登录）
2. **中优先级**：TaskManager 修改（删除 cookies）
3. **低优先级**：自动触发登录流程（需要前端轮询）
