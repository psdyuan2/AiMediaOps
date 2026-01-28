"""
Core Module - Core components for Multi-Agent System.

This module provides the foundational Context management system that serves as
the Single Source of Truth for agent execution lifecycle.

Main Components:
- Context: Main context class combining all layers
- MetaContext: Static meta-information layer
- RuntimeContext: Dynamic state management layer
- HistoryContext: Logging and memory layer
- LLMService: Structured reasoning engine for pure agentic architecture
- PromptEngine: Dynamic prompt rendering with Jinja2 templates
"""

from .context import (
    Context,
    MetaContext,
    RuntimeContext,
    HistoryContext,
    ActionLog,
    StepStatus,
)
from .llm import LLMService
from .prompts import PromptEngine, prompt_engine, render_template

__all__ = [
    "Context",
    "MetaContext",
    "RuntimeContext",
    "HistoryContext",
    "ActionLog",
    "StepStatus",
    "LLMService",
    "PromptEngine",
    "prompt_engine",
    "render_template",
]

__version__ = "1.0.0"
__author__ = "Senior Python Backend Architect"