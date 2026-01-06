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

        # 确保数据目录存在
        # os.makedirs(self._data_dir, exist_ok=True)

        # # 尝试从本地文件加载
        # if os.path.exists(self._file_path):
        #     self._local_load()
        # else:
        #     # 创建新的 meta 结构
        #     self._create_new_meta(**kwargs)

    def create_new_meta(self, **kwargs):
        """创建新的 meta 数据结构"""
        self.meta = {
            "task_id": self.task_id,
            "xhs_account_id": kwargs.get("xhs_account_id"),  # 任务账户ID
            "frequent": kwargs.get("frequent", 8),  # 单日任务运行频率，默认8次
            "valid_time_rage": kwargs.get("valid_time_rage", [8, 22]),  # 任务运行时间段，默认8点到22点
            "operate_accounts": {
                "xhs_accounts_info": kwargs.get("xhs_accounts_info", {})
            },
            "step": []  # 记录每一次任务执行时的参数
        }

        # 保存到本地
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
            self.step_id = len(data.get("step"))

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


