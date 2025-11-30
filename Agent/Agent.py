import json
import requests
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Type, Union
from pydantic import BaseModel, Field
from functools import wraps
from Agent.Context import AgentContext
from Agent.Tool import ToolRegistry


class BaseLLM(ABC):
    """LLM 抽象基类"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]]) -> str:
        pass

    def parse_json(self, content: str) -> Dict[str, Any]:
        """
        通用 JSON 解析器。
        能够处理大模型输出的Markdown格式，例如:
        ```json
        {"key": "value"}
        ```
        """
        try:
            # 1. 尝试直接解析
            return json.loads(content)
        except json.JSONDecodeError:
            # 2. 尝试提取 Markdown 代码块中的 JSON
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # 3. 尝试提取第一个 { ... } 结构
            json_match_bracket = re.search(r"(\{.*\})", content, re.DOTALL)
            if json_match_bracket:
                try:
                    return json.loads(json_match_bracket.group(1))
                except json.JSONDecodeError:
                    pass

            raise ValueError(f"Failed to parse JSON from LLM output: {content}")


class OpenAILLM(BaseLLM):
    """基于 OpenAI SDK 的实现 (兼容 OpenAI, DeepSeek, Moonshot 等)"""

    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o"):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            raise ImportError("Please install openai package: pip install openai")
        self.model = model

    def chat(self, messages: List[Dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"}  # 强制 JSON 模式 (如果模型支持)
        )
        return response.choices[0].message.content


class HttpLLM(BaseLLM):
    """通用的 HTTP 调用实现 (适用于自定义部署模型或特殊协议)"""

    def __init__(self, api_url: str, api_key: str, model: str = "default"):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    def chat(self, messages: List[Dict[str, str]]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # 假设返回格式遵循 OpenAI 标准，如果不遵循需根据实际情况修改
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return json.dumps({"error": str(e), "action": "fail"})


# ==========================================
# 4. Agent 基类 (核心逻辑)
# ==========================================

class Agent:
    def __init__(
            self,
            llm: BaseLLM,
            context: Optional[AgentContext] = None,
            tools: Optional[ToolRegistry] = None
    ):
        self.llm = llm
        self.context = context if context else AgentContext()
        self.tools = tools if tools else ToolRegistry()

        # 简单的系统提示词，告诉模型如何以 JSON 格式输出动作
        self.system_prompt = """
You are an intelligent agent.
You have access to the following tools:
{tool_descriptions}

You strictly respond in JSON format.
The JSON structure should be:
{{
    "thought": "Your reasoning process",
    "action_name": "name of the tool to use",
    "action_params": {{ "param_key": "param_value" }}
}}
If no tool is needed, set "action_name" to "finish" and provide a summary in "action_params".
"""

    def _build_system_message(self) -> str:
        tool_desc = self.tools.get_tools_description()
        return self.system_prompt.format(tool_descriptions=tool_desc)

    def run(self, task: str) -> Dict[str, Any]:
        """
        运行 Agent 的主循环 (简化版: 单次交互)
        """
        # 1. 初始化上下文
        self.context.add_message("system", self._build_system_message())
        self.context.add_message("user", task)

        print(f"[*] Agent thinking on task: {task}...")

        # 2. 调用 LLM
        raw_response = self.llm.chat(self.context.get_history())
        print(f"[*] LLM Raw Response: {raw_response}")

        # 3. 解析结果
        try:
            parsed_result = self.llm.parse_json(raw_response)
        except ValueError as e:
            print(f"[!] JSON Parse Error: {e}")
            return {"status": "error", "message": str(e)}

        # 4. 记录 LLM 回复到上下文
        self.context.add_message("assistant", raw_response)

        # 5. (此处可以添加自动执行 Tool 的逻辑)
        # action_name = parsed_result.get("action_name")
        # if action_name and action_name != "finish":
        #     tool = self.tools.get_tool(action_name)
        #     if tool:
        #         result = tool.execute(**parsed_result.get("action_params", {}))
        #         self.context.add_message("system", f"Tool Output: {result}")

        return parsed_result