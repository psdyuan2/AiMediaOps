基于您提供的 `xiaohongshu-mcp` 工具定义数据，我为您整理了一份完整的 MCP 工具调用接口文档。这份文档详细描述了每个工具的功能、参数结构及必填项，可以直接用于开发对接。

-----

# 小红书 MCP 工具调用接口文档 (Tools API)

本文档基于 `xiaohongshu-mcp` 提供的工具元数据整理，适用于通过 MCP 协议调用 `tools/call` 方法时的 `arguments` 参数构建。

## 1\. 账号与登录管理

### 1.1 检查登录状态

  * **工具名称 (`name`)**: `check_login_status`
  * **描述**: 检查当前小红书账号的登录状态。
  * **参数 (`arguments`)**: `{}` (空对象，无参数)

### 1.2 获取登录二维码

  * **工具名称 (`name`)**: `get_login_qrcode`
  * **描述**: 获取登录二维码。返回结果包含 Base64 格式的图片数据和超时时间。
  * **参数 (`arguments`)**: `{}` (空对象，无参数)

### 1.3 重置登录 (删除 Cookies)

  * **工具名称 (`name`)**: `delete_cookies`
  * **描述**: 删除本地 cookies 文件，重置登录状态。执行后需要重新扫码登录。
  * **参数 (`arguments`)**: `{}` (空对象，无参数)

### 1.4 获取用户主页信息

  * **工具名称 (`name`)**: `user_profile`
  * **描述**: 获取指定用户的个人主页信息（包含基本信息、粉丝数、获赞量及笔记列表）。
  * **参数 (`arguments`)**:

| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `user_id` | string | **是** | 小红书用户 ID (通常从搜索或 Feed 列表中获取) |
| `xsec_token` | string | **是** | 访问令牌 (通常从搜索或 Feed 列表中获取) |

-----

## 2\. 内容发布

### 2.1 发布图文笔记

  * **工具名称 (`name`)**: `publish_content`
  * **描述**: 发布带图片的图文笔记。
  * **参数 (`arguments`)**:

| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `title` | string | **是** | 笔记标题 (限制：最多 20 个字) |
| `content` | string | **是** | 正文内容 (不包含话题标签，标签请使用 tags 参数) |
| `images` | array[string] | **是** | 图片路径列表 (至少 1 张)。<br>支持：<br>1. HTTP/HTTPS URL<br>2. 本地绝对路径 (推荐，如 `/Users/user/1.jpg`) |
| `tags` | array[string] | 否 | 话题标签列表，例如 `["美食", "探店"]` |

### 2.2 发布视频笔记

  * **工具名称 (`name`)**: `publish_with_video`
  * **描述**: 发布视频笔记。
  * **参数 (`arguments`)**:

| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `title` | string | **是** | 笔记标题 (限制：最多 20 个字) |
| `content` | string | **是** | 正文内容 |
| `video` | string | **是** | **仅支持本地视频文件的绝对路径** (不支持 URL) |
| `tags` | array[string] | 否 | 话题标签列表 |

-----

## 3\. 内容获取与搜索

### 3.1 获取首页推荐列表

  * **工具名称 (`name`)**: `list_feeds`
  * **描述**: 获取小红书首页的推荐 Feed 流。
  * **参数 (`arguments`)**: `{}` (空对象，无参数)

### 3.2 搜索笔记

  * **工具名称 (`name`)**: `search_feeds`
  * **描述**: 根据关键词搜索内容 (需已登录)。
  * **参数 (`arguments`)**:

| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `keyword` | string | **是** | 搜索关键词 |
| `filters` | object | 否 | 筛选选项 (结构见下方) |

**`filters` 对象结构**:
| 属性名 | 类型 | 描述 | 可选值 |
| :--- | :--- | :--- | :--- |
| `sort_by` | string | 排序依据 | `综合` (默认), `最新`, `最多点赞`, `最多评论`, `最多收藏` |
| `note_type` | string | 笔记类型 | `不限` (默认), `视频`, `图文` |
| `publish_time`| string | 发布时间 | `不限` (默认), `一天内`, `一周内`, `半年内` |
| `search_scope`| string | 搜索范围 | `不限` (默认), `已看过`, `未看过`, `已关注` |
| `location` | string | 位置距离 | `不限` (默认), `同城`, `附近` |

### 3.3 获取笔记详情

  * **工具名称 (`name`)**: `get_feed_detail`
  * **描述**: 获取单篇笔记的详细信息（内容、图片、作者、互动数据、评论列表）。
  * **参数 (`arguments`)**:

| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `feed_id` | string | **是** | 笔记 ID |
| `xsec_token` | string | **是** | 访问令牌 |

-----

## 4\. 互动操作

### 4.1 发表评论

  * **工具名称 (`name`)**: `post_comment_to_feed`
  * **描述**: 在指定笔记下发表评论。
  * **参数 (`arguments`)**:

| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `feed_id` | string | **是** | 笔记 ID |
| `xsec_token` | string | **是** | 访问令牌 |
| `content` | string | **是** | 评论内容 |

### 4.2 点赞/取消点赞

  * **工具名称 (`name`)**: `like_feed`
  * **描述**: 对笔记进行点赞或取消点赞操作。
  * **参数 (`arguments`)**:

| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `feed_id` | string | **是** | 笔记 ID |
| `xsec_token` | string | **是** | 访问令牌 |
| `unlike` | boolean | 否 | `true`: 取消点赞; `false` (或不传): 点赞 |

### 4.3 收藏/取消收藏

  * **工具名称 (`name`)**: `favorite_feed`
  * **描述**: 对笔记进行收藏或取消收藏操作。
  * **参数 (`arguments`)**:

| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `feed_id` | string | **是** | 笔记 ID |
| `xsec_token` | string | **是** | 访问令牌 |
| `unfavorite` | boolean | 否 | `true`: 取消收藏; `false` (或不传): 收藏 |

-----

## 5\. 调用示例 (Python Payload)

以下是构造 JSON-RPC 请求体的示例：

**示例 1：发布图文**

```python
payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 1,
    "params": {
        "name": "publish_content",
        "arguments": {
            "title": "测试笔记",
            "content": "这是内容...",
            "images": ["/data/img1.jpg"],
            "tags": ["测试"]
        }
    }
}
```

**示例 2：带筛选条件的搜索**

```python
payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 2,
    "params": {
        "name": "search_feeds",
        "arguments": {
            "keyword": "Python教程",
            "filters": {
                "sort_by": "最多点赞",
                "note_type": "图文"
            }
        }
    }
}
```