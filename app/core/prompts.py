"""
Prompt Engine Module

This module provides dynamic prompt rendering capabilities using Jinja2 templates.
It manages template loading and rendering for the agent system.
"""

import os
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound


class PromptEngine:
    """
    Singleton prompt engine for loading and rendering Jinja2 templates.

    This class manages templates for dynamic prompt generation in the agent system.
    It follows a singleton pattern to ensure consistent template loading across
    the entire application.
    """

    _instance = None
    _environment: Environment = None

    def __new__(cls) -> 'PromptEngine':
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the prompt engine if not already initialized."""
        if self._initialized:
            return

        # Determine the templates directory path
        # Look for templates in app/prompts/ relative to the project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up from app/core/ to app/ and then to prompts/
        templates_dir = os.path.join(os.path.dirname(current_dir), 'prompts')

        if not os.path.exists(templates_dir):
            raise FileNotFoundError(
                f"Templates directory not found at {templates_dir}. "
                "Please ensure the app/prompts/ directory exists."
            )

        # Initialize Jinja2 environment
        self._environment = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=False,  # We're generating prompts, not HTML
            trim_blocks=True,
            lstrip_blocks=True
        )

        self._templates_dir = templates_dir
        self._initialized = True

        print(f"✅ PromptEngine initialized with templates directory: {templates_dir}")

    @property
    def environment(self) -> Environment:
        """Get the Jinja2 environment instance."""
        return self._environment

    def render(self, template_name: str, **kwargs: Any) -> str:
        """
        Render a template with the provided variables.

        Args:
            template_name: Name of the template file (without .jinja2 extension)
            **kwargs: Variables to pass to the template

        Returns:
            Rendered template as string

        Raises:
            TemplateNotFound: If the template file doesn't exist
            Exception: For template rendering errors
        """
        if not self._environment:
            raise RuntimeError("PromptEngine not properly initialized")

        try:
            # Ensure template name has .jinja2 extension
            if not template_name.endswith('.jinja2'):
                template_name = f"{template_name}.jinja2"

            # Load and render the template
            template = self._environment.get_template(template_name)
            return template.render(**kwargs)

        except TemplateNotFound as e:
            available_templates = self._environment.list_templates()
            raise TemplateNotFound(
                f"Template '{template_name}' not found. "
                f"Available templates: {available_templates}"
            ) from e
        except Exception as e:
            raise Exception(f"Error rendering template '{template_name}': {str(e)}") from e

    def get_template(self, template_name: str) -> Template:
        """
        Get a Jinja2 Template object for advanced usage.

        Args:
            template_name: Name of the template file

        Returns:
            Jinja2 Template object

        Raises:
            TemplateNotFound: If the template file doesn't exist
        """
        if not template_name.endswith('.jinja2'):
            template_name = f"{template_name}.jinja2"

        return self._environment.get_template(template_name)

    def list_templates(self) -> list[str]:
        """
        List all available templates.

        Returns:
            List of template names
        """
        if not self._environment:
            raise RuntimeError("PromptEngine not properly initialized")

        return self._environment.list_templates()

    def template_exists(self, template_name: str) -> bool:
        """
        Check if a template exists.

        Args:
            template_name: Name of the template file

        Returns:
            True if template exists, False otherwise
        """
        try:
            if not template_name.endswith('.jinja2'):
                template_name = f"{template_name}.jinja2"
            self._environment.get_template(template_name)
            return True
        except TemplateNotFound:
            return False

    def get_template_path(self, template_name: str) -> str:
        """
        Get the full file path for a template.

        Args:
            template_name: Name of the template file

        Returns:
            Full path to the template file
        """
        if not template_name.endswith('.jinja2'):
            template_name = f"{template_name}.jinja2"

        return os.path.join(self._templates_dir, template_name)


# Module-level singleton instance for easy access
prompt_engine = PromptEngine()


# Convenience functions for direct usage
def render_template(template_name: str, **kwargs: Any) -> str:
    """
    Convenience function to render a template.

    Args:
        template_name: Name of the template file
        **kwargs: Variables to pass to the template

    Returns:
        Rendered template as string
    """
    return prompt_engine.render(template_name, **kwargs)


def get_template_info() -> Dict[str, Any]:
    """
    Get information about the prompt engine.

    Returns:
        Dictionary with engine information
    """
    return {
        "templates_directory": prompt_engine._templates_dir,
        "available_templates": prompt_engine.list_templates(),
        "environment_initialized": prompt_engine._environment is not None
    }