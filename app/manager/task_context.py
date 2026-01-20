"""
任务上下文管理器模块

按照 Doc/manager_context.md 文档要求实现，专门用于 task manager 的上下文管理。
将任务管理器的上下文保存在一个 meta 对象中，并且能够进行序列化和反序列化。
即使任务暂停，task manager实例被回收，也可以通过上下文重新实例化，继续任务。

文件地址默认为 ./app/manager/data/mate_{task_id}.json
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from app.core.logger import logger

class Task_Manager_Context:
    """
    任务管理器上下文类

    功能：
    1. 将任务管理器的上下文保存在 meta 对象中
    2. 支持序列化和反序列化
    3. 支持任务中断后恢复
    4. 每次更新 meta 时自动序列化本地保存

    基础属性：
    - step_id: int - 当前步骤ID
    - meta: Dict - 元数据对象
    - task_id: str - 任务ID
    """

    def __init__(self, task_id: str, **kwargs):
        """
        初始化任务上下文管理器

        Args:
            task_id: 任务ID
        """
        self.task_id = task_id
        self.step_id = 1  # 默认从步骤1开始
        self.meta: Dict[str, Any] = {}

        # 文件存储路径
        # 1. 获取当前文件的绝对路径
        current_file_path = Path(__file__).resolve()
        self._data_dir = Path.joinpath(current_file_path.parent, "data/")
        self._file_path = os.path.join(self._data_dir, f"mate_{task_id}.json")

        # 维护数据：先检查本地文件是否存在
        if os.path.exists(self._file_path):
            # 文件存在，从本地加载（在 create_from_meta() 中会调用 _local_load）
            # 这里只标记文件已存在，实际的加载在 create_from_meta() 中完成
            pass
        else:
            # 文件不存在，确保目录存在（后续 create_new_meta 时会创建新文件）
            os.makedirs(self._data_dir, exist_ok=True)

    def create_new_meta(self, **kwargs):
        """创建新的 meta 数据结构"""
        # 如果文件已存在，不应该覆盖，应该加载现有数据
        if os.path.exists(self._file_path):
            logger.info(f"任务上下文文件已存在: {self._file_path}，加载已有数据而非创建新数据")
            self._local_load()
            return
        
        # 文件不存在，创建新的 meta 结构
        self.meta = {
            "task_id": self.task_id,
            "xhs_account_id": kwargs.get("xhs_account_id"),  # 任务账户ID
            "xhs_account_name": kwargs.get("xhs_account_name"),  # 任务账户名称
            "user_query": kwargs.get("user_query"),  # 用户查询内容
            "user_topic": kwargs.get("user_topic"),  # 帖子主题
            "user_style": kwargs.get("user_style"),  # 内容风格
            "user_target_audience": kwargs.get("user_target_audience"),  # 目标受众
            "task_type": kwargs.get("task_type"),  # 任务类型
            "frequent": kwargs.get("frequent", 8),  # 单日任务运行频率，默认8次
            "valid_time_rage": kwargs.get("valid_time_rage", [8, 22]),  # 任务运行时间段，默认8点到22点
            "valid_time_range": kwargs.get("valid_time_range", [8, 22]),  # 任务运行时间段（新字段名）
            "task_end_time": kwargs.get("task_end_time"),  # 任务结束时间
            "interval": kwargs.get("interval"),  # 执行间隔
            "mode": kwargs.get("mode", "standard"),  # 任务执行模式，默认为标准模式
            "interaction_note_count": kwargs.get("interaction_note_count", 3),  # 互动笔记数量，默认3
            "sys_type": kwargs.get("sys_type"),  # 保存系统类型，用于恢复任务时确定 MCP 二进制文件
            "operate_accounts": {
                "xhs_accounts_info": kwargs.get("xhs_accounts_info", {})
            },
            "step": []  # 记录每一次任务执行时的参数
        }

        # 确保目录存在后保存到本地
        os.makedirs(self._data_dir, exist_ok=True)
        self._local_save()

    def create_from_meta(self):
        self._local_load()

    def get_xhs_params(self):
        return self.meta.get('operate_accounts',{}).get('xhs_accounts_info', {})

    def _local_save(self):
        """将 meta 数据序列化存储到本地文件"""
        try:
            # 更新最后修改时间
            self.meta["last_updated"] = datetime.now().isoformat()

            save_data = {
                "meta": self.meta,
                "step_id": self.step_id,
                "task_id": self.task_id,
                "saved_at": datetime.now().isoformat()
            }

            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 任务上下文已保存: {self._file_path}")
        except Exception as e:
            logger.error(f"❌ 保存任务上下文失败: {e}")

    def _local_load(self):
        """从本地文件反序列化加载 meta 数据"""
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 恢复数据
            self.meta = data.get("meta", {})
            # 确保 step 不为 None
            # step 应该在 meta 中，而不是在顶层
            step_data = self.meta.get("step")
            if step_data is None:
                step_data = []
                logger.warning(f"任务上下文文件中的 meta.step 为 None，初始化为空列表")
                # 确保 meta 中有 step 字段
                self.meta["step"] = step_data
            self.step_id = data.get("step_id", 1)  # 从顶层获取 step_id，如果没有则默认为1
            # 如果 step_id 为 0 或 None，但 step 列表不为空，则使用 step 列表长度
            if (self.step_id == 0 or self.step_id is None) and isinstance(step_data, list) and len(step_data) > 0:
                self.step_id = len(step_data)

            logger.info(f"✅ 任务上下文已加载: {self._file_path}, 当前步骤数：{self.step_id}")
        except Exception as e:
            logger.warning(f"❌ 加载任务上下文失败: {e}")

    # ==================== 数据存储接口 ====================

    def save(self, data: Any, step_id: Optional[int] = None):
        """
        保存数据到 meta

        Args:
            data: 要保存的数据
            step_id: 步骤ID，如果指定则存储在 meta.step 中对应 step_id 的字段中
                    如果没有指定 step_id，则 step_id 默认为 self.step_id
        """
        if step_id is None:
            step_id = self.step_id

        # 确保 step 列表存在
        if "step" not in self.meta:
            self.meta["step"] = []

        # 查找或创建对应 step_id 的步骤记录
        step_found = False
        for i, step in enumerate(self.meta["step"]):
            if step.get("step_id") == step_id:
                # 更新现有步骤
                if isinstance(data, dict):
                    step.update(data)
                else:
                    step["data"] = data
                step["updated_at"] = datetime.now().isoformat()
                self.meta["step"][i] = step
                step_found = True
                break

        if not step_found:
            # 创建新的步骤记录
            step_data = {
                "step_id": step_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            if isinstance(data, dict):
                step_data.update(data)
            else:
                step_data["data"] = data

            self.meta["step"].append(step_data)

        # 自动保存到本地
        self._local_save()

    def update_meta(self, **kwargs):
        """
        更新 meta 中的指定字段
        
        Args:
            **kwargs: 要更新的字段，键名对应 meta 中的字段名
        """
        updated_fields = []
        for key, value in kwargs.items():
            if value is not None:  # 只更新非 None 的值
                self.meta[key] = value
                updated_fields.append(key)
        
        if updated_fields:
            # 自动保存到本地
            self._local_save()
            logger.info(f"任务上下文已更新字段: {', '.join(updated_fields)}")
        
        return updated_fields

    def get(self, key: str, step_id: Optional[int] = None) -> Any:
        """
        从 meta 中获取数据

        Args:
            key: 键名，支持点分隔的嵌套路径
            step_id: 步骤ID，如果指定则从 meta.step 中对应 step_id 的字段中获取
                    如果没有指定 step_id，则 step_id 默认为 self.step_id

        Returns:
            对应的值，如果不存在则返回 None
        """
        # 处理特殊的 step.key 格式，如 "step.1.action"
        if key.startswith("step."):
            parts = key.split('.')
            if len(parts) >= 2:
                # 尝试解析 step_id
                try:
                    step_id_from_key = int(parts[1])
                    step_id = step_id_from_key
                    # 剩余部分作为子键
                    sub_key = '.'.join(parts[2:]) if len(parts) > 2 else None
                except ValueError:
                    # 如果不是数字，使用默认 step_id
                    step_id = step_id if step_id is not None else self.step_id
                    sub_key = '.'.join(parts[1:])
            else:
                step_id = step_id if step_id is not None else self.step_id
                sub_key = None
        else:
            sub_key = key

        # 查找对应 step_id 的步骤
        step_data = None
        if key.startswith("step."):
            for step in self.meta.get("step", []):
                if step.get("step_id") == step_id:
                    step_data = step
                    break

            if step_data is None:
                return None

            # 如果没有子键，返回整个步骤数据
            if sub_key is None or sub_key == "":
                return step_data

            return self._get_nested_value(step_data, sub_key)
        else:
            # 从 meta 根目录获取
            return self._get_nested_value(self.meta, key)

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """获取嵌套字典中的值"""
        keys = key.split('.')
        value = data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None

        return value


    def set_step_id(self, step_id: int):
        """设置当前步骤ID"""
        self.step_id = step_id
        self._local_save()

    def next_step(self):
        """前进到下一步"""
        self.step_id += 1
        self._local_save()

    def get_file_path(self) -> str:
        """获取上下文文件路径"""
        return self._file_path



    def __str__(self) -> str:
        """字符串表示"""
        return f"Task_Manager_Context(task_id={self.task_id}, step_id={self.step_id})"

    def __repr__(self) -> str:
        """详细表示"""
        return f"Task_Manager_Context(task_id='{self.task_id}', step_id={self.step_id}, file_path='{self._file_path}')"


