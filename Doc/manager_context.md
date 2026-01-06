# 任务上下文管理器 task_context
## 功能描述
将任务管理器的上下文保存在一个meta对象中，并且能够进行序列化和反序列化，即使任务暂停，
task manager实例被回收，也可以通过上下文重新实例化，继续任务.  
Task_context对象通过task_id被创建后，能够通过接口，将task manager的参数保存在自身的meta
对象当中，并在每次更新meta时，自动序列化本地保存。

## 核心模块

### 基础属性：  
* step_id: int
* meta
* task_id
* 其他meta中非step参数

### 初始化接口
#### init_by_meta()
如果本地已经有保存好的meta序列化文件，则通过反序列化meta文件方式，进行初始化
可以通过from_dict从本地文件获取
文件地址默认为 ./app/manager/data/mate_{task_id}.json

#### create_new()
构建一个新的meta数据结构

### meta数据结构
```python
class Task_Manager_Context_Meta:
    task_id: str
    task_account_id: str
    frequent: int # 单日任务运行频率
    valid_time_rage: [int] # 任务运行时间段
    operate_accounts: dict # 该任务所有关联的账号信息
    step: [dict] # 记录每一次任务执行时的参数
```
示例：

```python
meta.task_id = 'start'
meta.task_account_id = 'test1'
meta.frequent = 8
meta.valid_time_range = [8, 22]
meta.operate_accounts = {
    "xhs_accounts": {
        "xhs_account_id": "",
        "xhs_account_name": ""
        # 帮我补充剩下的xhs agent创建时的其他参数
    }
}
meta.step = [
    {
        "step_id": 1,
        # 暂时置空，我在开发task manager时再通过接口添加
    }
]
```

### meta数据序列化存储和反序列化重构

#### _local_save
#### _local_load

## 数据存储接口
### save(data: Any, step_id: int)
如果指定step_id,将数据存储在meta中step字段step_id一致的的字段中  
如果没有指定step_id,则step_id默认为self.step_id

### get(key, step_id: int)
主要逻辑和save函数一致




