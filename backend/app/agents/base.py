"""
Base Agent Module

This module provides the abstract base class for all agents in the system.
It includes tool registration, prompt rendering, and common agent functionality.
"""

import inspect
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Type, Union
from pydantic import BaseModel, Field

from app.core.context import Context
from app.core.llm import LLMService
from app.core.prompts import PromptEngine, prompt_engine


class AgentTool(BaseModel):
    """
    Represents a tool that can be used by an agent.

    This model contains metadata about an agent's tool method
    including its name, description, and the callable function.
    """
    name: str = Field(description="Unique name of the tool")
    description: str = Field(description="Description of what the tool does")
    func: Callable = Field(description="The actual function to call")
    signature: str = Field(description="Function signature for documentation")


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.

    This class provides common functionality for agents including:
    - Automatic tool registration via @tool decorator
    - Prompt rendering with automatic context injection
    - LLM integration
    - Context management
    """

    def __init__(self, context: Context, llm: LLMService) -> None:
        """
        Initialize the base agent.

        Args:
            context: The context object containing system state
            llm: The LLM service for generating responses
        """
        self.context = context
        self.llm = llm
        self.prompt_engine: PromptEngine = prompt_engine
        self.tools: Dict[str, AgentTool] = {}

        # Automatically register decorated methods
        self._register_class_tools()

    @staticmethod
    def tool(name: Optional[str] = None, description: Optional[str] = None):
        """
        Decorator to mark a method as an agent tool.

        Args:
            name: Optional custom name for the tool (defaults to method name)
            description: Optional description of what the tool does

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            # Store tool metadata as function attributes
            func._is_tool = True
            func._tool_name = name or func.__name__
            func._tool_description = description or (
                func.__doc__.strip() if func.__doc__ else f"Tool method: {func.__name__}"
            )
            return func

        return decorator

    def _register_class_tools(self) -> None:
        """
        Scan instance methods and register those marked with @tool decorator.

        This method is called during initialization and discovers all methods
        that have been decorated with @tool, adding them to the tools registry.
        """
        # Get all methods of this instance
        for attr_name in dir(self):
            attr = getattr(self, attr_name)

            # Check if it's a method and has tool attributes
            if (
                callable(attr) and
                hasattr(attr, '_is_tool') and
                attr._is_tool and
                not attr_name.startswith('_')  # Skip private methods
            ):
                # Get tool information
                tool_name = getattr(attr, '_tool_name', attr_name)
                tool_description = getattr(attr, '_tool_description', '')

                # Create function signature string
                sig = inspect.signature(attr)
                signature_str = f"{attr_name}{sig}"

                # Create and register the tool
                tool = AgentTool(
                    name=tool_name,
                    description=tool_description,
                    func=attr,
                    signature=signature_str
                )

                self.tools[tool_name] = tool

        print(f" {self.__class__.__name__} registered {len(self.tools)} tools: {list(self.tools.keys())}")

    def get_tool(self, tool_name: str) -> Optional[AgentTool]:
        """
        Get a tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            AgentTool instance if found, None otherwise
        """
        return self.tools.get(tool_name)

    def list_tools(self) -> list[str]:
        """
        Get list of available tool names.

        Returns:
            List of tool names
        """
        return list(self.tools.keys())

    def get_tools_info(self) -> Dict[str, Dict[str, str]]:
        """
        Get detailed information about all registered tools.

        Returns:
            Dictionary mapping tool names to their metadata
        """
        return {
            name: {
                "description": tool.description,
                "signature": tool.signature
            }
            for name, tool in self.tools.items()
        }

    def render_prompt(self, template_name: str, **kwargs: Any) -> str:
        """
        Render a prompt template with automatic context injection.

        This method provides a shortcut to template rendering that automatically
        includes the agent's context in the template variables, so subclasses
        don't have to pass it manually every time.

        Args:
            template_name: Name of the template file
            **kwargs: Additional variables to pass to the template

        Returns:
            Rendered template as string

        Raises:
            Exception: If template rendering fails
        """
        # Automatically inject context into template variables
        template_vars = {
            'context': self.context,
            'agent': self,
            'tools': self.tools,
            'tools_info': self.get_tools_info(),
            **kwargs  # Allow override of injected variables
        }

        try:
            return self.prompt_engine.render(template_name, **template_vars)
        except Exception as e:
            raise Exception(
                f"Failed to render template '{template_name}' for agent '{self.__class__.__name__}': {str(e)}"
            ) from e

    async def call_tool(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Call a registered tool by name.

        Args:
            tool_name: Name of the tool to call
            *args: Positional arguments for the tool
            **kwargs: Keyword arguments for the tool

        Returns:
            Result of the tool function

        Raises:
            ValueError: If the tool doesn't exist
            Exception: If the tool execution fails
        """
        if tool_name not in self.tools:
            available_tools = list(self.tools.keys())
            raise ValueError(
                f"Tool '{tool_name}' not found. "
                f"Available tools: {available_tools}"
            )

        tool = self.tools[tool_name]

        try:
            # Call the tool function
            result = await tool.func(*args, **kwargs) if inspect.iscoroutinefunction(tool.func) else tool.func(*args, **kwargs)
            return result
        except Exception as e:
            raise Exception(f"Error executing tool '{tool_name}': {str(e)}") from e

    async def generate_with_prompt(
        self,
        template_name: str,
        response_model: Type[BaseModel],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        **template_vars: Any
    ) -> BaseModel:
        """
        Generate LLM response using a prompt template.

        This method combines prompt rendering and LLM generation for convenience.

        Args:
            template_name: Name of the template to render
            response_model: Pydantic model for structured output
            system_prompt: Optional system prompt for the LLM
            temperature: Sampling temperature
            **template_vars: Additional variables for template rendering

        Returns:
            Instance of response_model with LLM-generated data
        """
        # Render the prompt
        prompt = self.render_prompt(template_name, **template_vars)

        # Generate LLM response
        result = await self.llm.generate(
            prompt=prompt,
            response_model=response_model,
            system_prompt=system_prompt,
            temperature=temperature
        )

        return result

    @abstractmethod
    async def run(self) -> Any:
        """
        Abstract method that must be implemented by subclasses.

        This method defines the main execution logic for the agent.
        Each agent type should implement its specific behavior here.

        Returns:
            Result of agent execution (type depends on specific agent)

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement the run() method")

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(tools={len(self.tools)})"

    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return (
            f"{self.__class__.__name__}("
            f"tools={list(self.tools.keys())}, "
            f"context_available={self.context is not None}, "
            f"llm_available={self.llm is not None}"
            f")"
        )