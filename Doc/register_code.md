## 域名：http://175.24.40.127/

## 产品: 墨客MoKe (ID: 1)

**接口地址**: `POST /api/licenses/verify`

**请求体**:
```json
{
  "product_id": 1,
  "license_code": "your_license_code_here"
}
```

**成功响应** (200):
```json
{
  "success": true,
  "config": {
  "end_time": "2024-12-31T23:59:59",
  "is_free": false,
  "price": 100,
  "task_num": 100
}
}
```

**字段配置** (field_config):
```json
{
  "end_time": "datetime", # 激活后到期时间
  "is_free": "boolean", # 是否是免费试用版本（用于注册机统计，和产品本身无关）
  "price": "number", # 订阅价格（用于注册机统计，和产品本身无关）
  "task_num": "number" # 可使用任务数量（调度器中总共可构建的任务数）
}
```

⚠️ **注意**：响应中的 `config` 字段内容基于产品的字段配置，不同产品返回的字段会有所不同。

