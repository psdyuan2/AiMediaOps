# 小红书 MCP 项目 (Python 版本)

基于 Playwright 的多浏览器实例管理，支持沙盒隔离和指纹配置，通过 MCP 协议提供完整的小红书操作工具。

## 🚀 项目特色

- **Python 重构**: 基于原 Go 版本重构，提供更灵活的 Python 生态集成
- **完整功能**: 支持登录、发布、搜索、评论、点赞、收藏等所有核心操作
- **多实例沙盒**: 支持多个浏览器实例并行运行，完全隔离
- **指纹管理**: 预定义和自定义浏览器指纹配置
- **MCP 协议**: 标准 MCP 协议，兼容 Claude Desktop 等客户端

## 📁 项目架构

```
app/xhs_mcp/
├── browser/              # 浏览器实例池管理
│   ├── __init__.py
│   └── pool.py           # 浏览器实例池
├── config/               # 配置管理
│   ├── __init__.py
│   └── fingerprint_manager.py  # 指纹配置管理
├── core/                 # 核心数据模型
│   ├── __init__.py
│   └── models.py         # 数据模型定义
├── services/             # 小红书操作服务
│   ├── __init__.py
│   └── xhs_service.py    # 小红书操作逻辑
├── mcp_server/           # MCP 服务器 (重命名避免冲突)
│   ├── __init__.py
│   └── server.py         # MCP 服务器实现
├── __init__.py           # 项目入口
├── run_mcp_server.py     # MCP 服务器启动脚本
├── test_basic.py         # 基础功能测试
├── test_mcp_simple.py    # 简化版 MCP 测试
├── example_ai_quant_comment.py      # AI 量化评论示例
├── example_mcp_ai_quant_comment.py  # MCP AI 量化评论示例
└── test_ai_quant_example.py         # AI 量化示例测试
```

## 🔧 核心功能

### 1. 多浏览器实例管理

- **浏览器实例池**: 管理多个浏览器实例，支持并发操作
- **沙盒隔离**: 每个实例完全隔离，支持多账号并行
- **状态管理**: 运行、暂停、停止、错误等状态管理
- **资源控制**: 限制最大实例数量，防止资源耗尽
- **实例持久化**: 切换账号时保持实例运行，支持手动管理

### 2. 指纹配置管理

- **预定义指纹**: 提供 Windows Chrome、macOS Chrome、Windows Edge、macOS Safari 等指纹配置
- **自定义指纹**: 支持创建和保存自定义指纹配置
- **指纹特征**: User-Agent、视口、语言、时区、平台、硬件信息等

### 3. 小红书完整操作服务

#### 基础操作
- **登录功能**: 支持小红书账号登录
- **发布笔记**: 发布图文笔记，支持图片和标签
- **内容搜索**: 搜索小红书内容
- **用户资料**: 获取用户个人信息
- **会话管理**: 登录状态检查和退出登录

#### 交互操作
- **发表评论**: 对指定笔记发表评论
- **点赞/取消点赞**: 点赞或取消点赞笔记
- **收藏/取消收藏**: 收藏或取消收藏笔记
- **Feed 列表**: 获取首页 Feed 列表

### 4. MCP 服务器

- **工具注册**: 自动注册所有操作工具
- **标准协议**: 遵循 MCP 协议标准
- **错误处理**: 完善的错误处理和日志记录
- **资源管理**: 自动清理浏览器资源

## 🚀 快速开始

### 安装依赖

```bash
# 安装 Playwright 浏览器
playwright install chromium

# 安装项目依赖
pip install playwright pytest pytest-asyncio mcp
```

### 运行示例

```bash
# 运行基础功能测试
python -m app.xhs_mcp.test_basic

# 运行完整示例
python -m app.xhs_mcp.example
```

### 启动 MCP 服务器

```bash
# 启动 MCP 服务器
python -m app.xhs_mcp.run_mcp_server
```

## 🛠️ MCP 工具列表

服务器提供以下完整工具集：

### 浏览器管理
1. **create_browser_instance** - 创建新的浏览器实例
2. **list_browser_instances** - 列出所有浏览器实例
3. **pause_browser_instance** - 暂停浏览器实例
4. **resume_browser_instance** - 恢复浏览器实例
5. **stop_browser_instance** - 停止浏览器实例
6. **list_fingerprints** - 列出所有可用的指纹配置

### 小红书操作
7. **xhs_login** - 小红书登录
8. **xhs_publish_note** - 发布小红书图文笔记
9. **xhs_search** - 小红书搜索
10. **xhs_post_comment** - 发表评论到指定笔记
11. **xhs_like_feed** - 点赞/取消点赞指定笔记
12. **xhs_favorite_feed** - 收藏/取消收藏指定笔记
13. **xhs_list_feeds** - 获取 Feed 列表

## 📝 使用示例

### 🎯 AI 量化交易帖子评论示例

项目提供了完整的 AI 量化交易帖子评论工作流示例：

#### 1. 基础示例 (`example_ai_quant_comment.py`)

```bash
# 运行基础示例
python example_ai_quant_comment.py
```

这个示例演示了完整的 MCP 调用流程：
- 创建浏览器实例
- 登录小红书账号
- 搜索 AI 量化相关帖子
- 发表专业评论
- 点赞帖子

#### 2. MCP 客户端示例 (`example_mcp_ai_quant_comment.py`)

```bash
# 运行 MCP 客户端示例
python example_mcp_ai_quant_comment.py
```

这个版本模拟了实际的 MCP 协议调用，更接近真实的 MCP 客户端实现。

#### 3. 测试脚本 (`test_ai_quant_example.py`)

```bash
# 测试示例功能
python test_ai_quant_example.py
```

验证所有示例脚本的基本功能。

### 创建浏览器实例

```python
from app.xhs_mcp.browser.pool import BrowserPool
from app.xhs_mcp.config.fingerprint_manager import FingerprintManager

# 初始化
pool = BrowserPool()
await pool.initialize()

# 创建配置
manager = FingerprintManager()
profile = manager.create_browser_profile(
    name="我的配置",
    fingerprint_name="windows_chrome",
    headless=False
)

# 创建实例
instance = await pool.create_instance(profile)
print(f"实例ID: {instance.instance_id}")
```

### 小红书完整操作

```python
import asyncio
from app.xhs_mcp.browser.pool import BrowserPool
from app.xhs_mcp.config.fingerprint_manager import FingerprintManager
from app.xhs_mcp.services.xhs_service import XHSService

async def main():
    # 初始化浏览器池
    pool = BrowserPool()
    await pool.initialize()

    # 创建浏览器实例
    manager = FingerprintManager()
    profile = manager.create_browser_profile(
        name="我的配置",
        fingerprint_name="windows_chrome",
        headless=False
    )
    instance = await pool.create_instance(profile)

    # 创建服务
    service = XHSService(pool)

    # 登录
    account = await service.login(
        instance_id=instance.instance_id,
        username="your_username",
        password="your_password"
    )
    print(f"登录成功: {account.username}")

    # 搜索
    results = await service.search(
        instance_id=instance.instance_id,
        keyword="Python编程",
        limit=5
    )
    print(f"搜索到 {len(results)} 个结果")

    # 获取 Feed 列表
    feeds = await service.list_feeds(instance_id=instance.instance_id, limit=5)
    print(f"获取到 {len(feeds)} 个 Feed")

    # 点赞笔记 (需要真实的笔记ID)
    # await service.like_feed(instance_id=instance.instance_id, feed_id="笔记ID")

    # 收藏笔记 (需要真实的笔记ID)
    # await service.favorite_feed(instance_id=instance.instance_id, feed_id="笔记ID")

    # 发表评论 (需要真实的笔记ID)
    # await service.post_comment(
    #     instance_id=instance.instance_id,
    #     feed_id="笔记ID",
    #     content="很好的内容，学习了！"
    # )

    # 清理资源
    await pool.cleanup()

# 运行
asyncio.run(main())
```

## 配置说明

### 指纹配置

项目提供以下预定义指纹：

- **windows_chrome**: Windows Chrome 浏览器指纹
- **macos_chrome**: macOS Chrome 浏览器指纹
- **windows_edge**: Windows Edge 浏览器指纹
- **macos_safari**: macOS Safari 浏览器指纹

### 浏览器配置

支持以下浏览器启动参数：

- `headless`: 是否无头模式
- `slow_mo`: 操作延迟(ms)
- `user_data_dir`: 用户数据目录
- `proxy`: 代理设置

## 🔧 开发说明

### 添加新工具

在 `mcp_server/server.py` 中的 `_register_tools` 方法添加新工具定义。

### 扩展小红书功能

在 `services/xhs_service.py` 中添加新的操作方法。

### 自定义指纹配置

使用 `FingerprintManager.create_custom_fingerprint()` 方法创建自定义指纹。

## 🖥️ Claude Desktop 集成

### 配置 MCP 服务器

在 Claude Desktop 的配置文件中添加：

```json
{
  "mcpServers": {
    "xhs-mcp": {
      "command": "python",
      "args": ["-m", "app.xhs_mcp.run_mcp_server"]
    }
  }
}
```

### 使用流程

1. **启动 Claude Desktop**
2. **创建浏览器实例**: 使用 `create_browser_instance` 工具
3. **登录小红书**: 使用 `xhs_login` 工具
4. **执行操作**: 发布笔记、搜索、评论、点赞等
5. **管理实例**: 使用暂停、恢复、停止工具管理实例

## 🎯 Python 版本优势

相比原 Go 版本，Python 版本提供：

- **更丰富的生态**: 集成 Python 数据科学、AI 等工具链
- **更灵活的扩展**: 易于添加新的功能模块
- **更好的调试**: Python 强大的调试和测试工具
- **异步支持**: 原生 async/await 支持，性能更好
- **类型安全**: Pydantic v2 提供完整类型检查和数据验证

## ⚠️ 注意事项

1. **账号安全**: 请妥善保管小红书账号信息
2. **合规使用**: 请遵守小红书平台规则和相关法律法规
3. **资源管理**: 及时清理不再使用的浏览器实例
4. **网络环境**: 确保稳定的网络连接
5. **依赖安装**: 确保正确安装 Playwright 浏览器

## 📄 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和平台规则。