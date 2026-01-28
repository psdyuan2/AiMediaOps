"""
Agents Module - Core Agent Infrastructure

This module provides the foundational components for building multi-agent systems:
- BaseAgent: Abstract base class for all agents
- AgentTool: Tool representation model
- Tool registration system
- Dynamic prompt rendering integration

The agent system supports:
- Automatic tool discovery and registration via @tool decorator
- Dynamic prompt rendering with context injection
- LLM integration for structured decision making
- Context management and state tracking
"""

from .base import BaseAgent, AgentTool

__all__ = [
    "BaseAgent",
    "AgentTool",
]

__version__ = "1.0.0"
__author__ = "Senior Python Backend Architect"