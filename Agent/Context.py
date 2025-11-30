import json
import requests
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Type, Union
from pydantic import BaseModel, Field
from functools import wraps


# ==========================================
# 1. Context 模块 (上下文管理)
# ==========================================

class AgentContext:
    """
    上下文管理对象，用于存储对话历史、Agent状态以及运行时变量。
    """

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []  # 存储对话历史 [{"role": "user", "content": "..."}]
        self.state: Dict[str, Any] = {}  # 存储运行时共享状态

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, Any]]:
        return self.messages

    def update_state(self, key: str, value: Any):
        self.state[key] = value

    def get_state(self, key: str, default=None) -> Any:
        return self.state.get(key, default)

    def clear_history(self):
        self.messages = []