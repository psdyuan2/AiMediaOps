from Agent.Agent import Agent, BaseLLM
from Agent.Context import AgentContext
from Agent.Tool import ToolRegistry
from typing import List, Dict, Any, Optional, Callable
import uuid
from datetime import datetime
import json


class MasterAgent(Agent):
    """
    MasterAgent - 增强版 Agent，具有多任务管理、子Agent协调、记忆管理等功能
    """

    def __init__(
        self,
        llm: BaseLLM,
        context: Optional[AgentContext] = None,
        tools: Optional[ToolRegistry] = None,
        max_tasks: int = 10,
        memory_enabled: bool = True,
        sub_agents: Optional[Dict[str, 'Agent']] = None
    ):
        """
        初始化 MasterAgent

        Args:
            llm: 语言模型实例
            context: 上下文管理器
            tools: 工具注册器
            max_tasks: 最大并发任务数
            memory_enabled: 是否启用记忆功能
            sub_agents: 子Agent字典
        """
        super().__init__(llm, context, tools)

        # MasterAgent 特有属性
        self.max_tasks = max_tasks
        self.memory_enabled = memory_enabled
        self.sub_agents = sub_agents or {}
        self.active_tasks = {}  # 活跃任务 {task_id: task_info}
        self.completed_tasks = {}  # 已完成任务
        self.long_term_memory = {}  # 长期记忆存储
        self.task_queue = []  # 任务队列

        # 增强 MasterAgent 的系统提示词
        self.system_prompt = """
You are a Master Agent with advanced capabilities including:
- Multi-task management and coordination
- Sub-agent delegation and supervision
- Long-term memory and learning
- Complex planning and execution

Available Tools:
{tool_descriptions}

Available Sub-agents:
{sub_agent_descriptions}

You strictly respond in JSON format. The JSON structure should be:
{{
    "thought": "Your reasoning process and strategy",
    "action_name": "name of the tool or sub-agent to use",
    "action_params": {{ "param_key": "param_value" }},
    "task_type": "main_task|delegation|coordination|memory",
    "priority": "high|medium|low"
}}
If no tool is needed, set "action_name" to "finish" and provide a summary in "action_params".
"""

    def _get_sub_agent_descriptions(self) -> str:
        """获取子Agent的描述信息"""
        if not self.sub_agents:
            return "No sub-agents available."

        descriptions = "Available Sub-agents:\n"
        for name, agent in self.sub_agents.items():
            descriptions += f"- {name}: {type(agent).__name__}\n"
        return descriptions

    def _build_system_message(self) -> str:
        """构建增强的系统消息"""
        tool_desc = self.tools.get_tools_description()
        sub_agent_desc = self._get_sub_agent_descriptions()
        return self.system_prompt.format(
            tool_descriptions=tool_desc,
            sub_agent_descriptions=sub_agent_desc
        )

    def add_sub_agent(self, name: str, agent: Agent):
        """添加子Agent"""
        self.sub_agents[name] = agent

    def remove_sub_agent(self, name: str) -> bool:
        """移除子Agent"""
        return self.sub_agents.pop(name, None) is not None

    def create_task(self, task_description: str, priority: str = "medium", task_type: str = "main_task") -> str:
        """
        创建新任务

        Args:
            task_description: 任务描述
            priority: 优先级 (high/medium/low)
            task_type: 任务类型

        Returns:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())

        if len(self.active_tasks) >= self.max_tasks:
            # 如果活跃任务已满，加入队列
            self.task_queue.append({
                "task_id": task_id,
                "description": task_description,
                "priority": priority,
                "task_type": task_type,
                "created_at": datetime.now()
            })
        else:
            # 直接创建任务
            self.active_tasks[task_id] = {
                "description": task_description,
                "priority": priority,
                "task_type": task_type,
                "status": "pending",
                "created_at": datetime.now(),
                "result": None
            }

        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.active_tasks.get(task_id) or self.completed_tasks.get(task_id)

    def delegate_to_sub_agent(self, sub_agent_name: str, task: str, **kwargs) -> Dict[str, Any]:
        """
        将任务委托给子Agent

        Args:
            sub_agent_name: 子Agent名称
            task: 任务描述
            **kwargs: 额外参数

        Returns:
            任务执行结果
        """
        if sub_agent_name not in self.sub_agents:
            return {
                "status": "error",
                "message": f"Sub-agent '{sub_agent_name}' not found"
            }

        sub_agent = self.sub_agents[sub_agent_name]
        try:
            result = sub_agent.run(task)
            return {
                "status": "success",
                "sub_agent": sub_agent_name,
                "result": result
            }
        except Exception as e:
            return {
                "status": "error",
                "sub_agent": sub_agent_name,
                "message": str(e)
            }

    def store_memory(self, key: str, value: Any, category: str = "general"):
        """
        存储长期记忆

        Args:
            key: 记忆键
            value: 记忆值
            category: 记忆类别
        """
        if not self.memory_enabled:
            return

        if category not in self.long_term_memory:
            self.long_term_memory[category] = {}

        self.long_term_memory[category][key] = {
            "value": value,
            "created_at": datetime.now(),
            "accessed_count": 0
        }

    def retrieve_memory(self, key: str, category: str = "general") -> Optional[Any]:
        """
        检索长期记忆

        Args:
            key: 记忆键
            category: 记忆类别

        Returns:
            记忆值或None
        """
        if not self.memory_enabled:
            return None

        if category in self.long_term_memory and key in self.long_term_memory[category]:
            memory = self.long_term_memory[category][key]
            memory["accessed_count"] += 1
            return memory["value"]

        return None

    def list_memories(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """
        列出记忆

        Args:
            category: 指定类别，None表示所有类别

        Returns:
            记忆键的字典
        """
        if not self.memory_enabled:
            return {}

        if category:
            return {category: list(self.long_term_memory.get(category, {}).keys())}

        return {cat: list(memories.keys()) for cat, memories in self.long_term_memory.items()}

    def process_task_queue(self):
        """处理任务队列"""
        while self.task_queue and len(self.active_tasks) < self.max_tasks:
            # 按优先级排序任务
            self.task_queue.sort(key=lambda x: (
                0 if x["priority"] == "high" else 1 if x["priority"] == "medium" else 2,
                x["created_at"]
            ))

            task = self.task_queue.pop(0)
            self.active_tasks[task["task_id"]] = {
                **task,
                "status": "pending",
                "result": None
            }

    def get_agent_stats(self) -> Dict[str, Any]:
        """获取MasterAgent的统计信息"""
        return {
            "active_tasks": len(self.active_tasks),
            "queued_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "sub_agents": list(self.sub_agents.keys()),
            "memory_categories": list(self.long_term_memory.keys()) if self.memory_enabled else [],
            "memory_enabled": self.memory_enabled,
            "max_tasks": self.max_tasks
        }

    def run_enhanced(self, task: str, use_memory: bool = True, enable_delegation: bool = True) -> Dict[str, Any]:
        """
        增强版运行方法

        Args:
            task: 任务描述
            use_memory: 是否使用记忆功能
            enable_delegation: 是否启用任务委托

        Returns:
            执行结果
        """
        # 创建任务记录
        task_id = self.create_task(task)

        # 存储到记忆中（如果启用）
        if use_memory and self.memory_enabled:
            self.store_memory(f"task_{task_id}", {
                "task": task,
                "created_at": datetime.now()
            }, "tasks")

        # 执行基础Agent逻辑
        result = super().run(task)

        # 如果启用委托且有委托请求
        if enable_delegation and result.get("action_name") == "delegate":
            sub_agent = result.get("action_params", {}).get("sub_agent")
            sub_task = result.get("action_params", {}).get("task")

            if sub_agent and sub_task:
                delegation_result = self.delegate_to_sub_agent(sub_agent, sub_task)
                result["delegation_result"] = delegation_result

        # 更新任务状态
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = "completed"
            self.active_tasks[task_id]["result"] = result
            self.active_tasks[task_id]["completed_at"] = datetime.now()

            # 移动到已完成任务
            self.completed_tasks[task_id] = self.active_tasks.pop(task_id)

        # 处理任务队列
        self.process_task_queue()

        return result
