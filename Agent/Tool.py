import json
import requests
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Type, Union
from pydantic import BaseModel, Field
from functools import wraps

class Tool(BaseModel):
    """
    工具对象定义，包含名称、描述、执行函数和参数结构。
    """
    name: str
    description: str
    func: Callable
    argument_schema: Optional[Type[BaseModel]] = None

    class Config:
        arbitrary_types_allowed = True

    def execute(self, **kwargs):
        return self.func(**kwargs)

class ToolRegistry:
    """
    工具注册器，提供装饰器 @tool 用于注册函数。
    """
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str, argument_schema: Optional[Type[BaseModel]] = None):
        """
        装饰器函数，仿照 browser-use 的风格
        """
        def decorator(func):
            tool_instance = Tool(
                name=name,
                description=description,
                func=func,
                argument_schema=argument_schema
            )
            self.tools[name] = tool_instance
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def get_tools_description(self) -> str:
        """生成供 LLM 阅读的工具描述 Prompt"""
        desc = "Available Tools:\n"
        for name, tool in self.tools.items():
            schema_json = tool.argument_schema.schema_json() if tool.argument_schema else "{}"
            desc += f"- {name}: {tool.description}\n  Args Schema: {schema_json}\n"
        return desc