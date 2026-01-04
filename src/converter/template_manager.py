"""
Template Manager for Code Generation

Manages Jinja2 templates and provides template context builders.
"""

import os
from pathlib import Path
from typing import Dict, Any, Callable
from jinja2 import Environment, FileSystemLoader, select_autoescape
import logging

logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Manage Jinja2 templates for Python code generation.

    Loads templates from the templates directory and provides rendering
    with custom filters and functions.

    Example:
        >>> manager = TemplateManager()
        >>> context = {'class_name': 'MyStrategy', 'inputs': []}
        >>> code = manager.render_strategy(context)
    """

    def __init__(self, template_dir: str = None):
        """
        Initialize template manager.

        Args:
            template_dir: Path to templates directory.
                        If None, uses default converter/templates/
        """
        if template_dir is None:
            # Default to templates/ subdirectory
            current_dir = Path(__file__).parent
            template_dir = str(current_dir / 'templates')

        logger.debug(f"Loading templates from: {template_dir}")

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Add custom filters
        self._register_custom_filters()

    def _register_custom_filters(self):
        """Register custom Jinja2 filters."""
        # Indent filter
        self.env.filters['indent'] = self._indent_filter

        # Python type conversion filter
        self.env.filters['to_python_type'] = self._to_python_type_filter

        # Join with commas
        self.env.filters['comma_join'] = lambda items: ', '.join(str(i) for i in items)

    def render_strategy(self, context: Dict[str, Any]) -> str:
        """
        Render complete strategy class.

        Args:
            context: Template context dictionary

        Returns:
            Rendered Python code

        Example:
            >>> manager = TemplateManager()
            >>> context = {
            ...     'class_name': 'MyStrategy',
            ...     'metadata': {'strategy_name': 'My Strategy'},
            ...     'imports': 'import pandas as pd',
            ...     'inputs': []
            ... }
            >>> code = manager.render_strategy(context)
            >>> 'class MyStrategy' in code
            True
        """
        template = self.env.get_template('strategy_template.py.jinja2')
        return template.render(context)

    def render_inputs_section(self, inputs: list) -> str:
        """
        Render inputs initialization section.

        Args:
            inputs: List of input dictionaries

        Returns:
            Rendered code
        """
        # Simple rendering without separate template
        lines = []
        for inp in inputs:
            name = inp.get('name')
            default = inp.get('default_value')
            title = inp.get('title', '')
            comment = f"  # {title}" if title else ""
            lines.append(f'self.{name} = self.params.get("{name}", {default}){comment}')

        return '\n'.join(lines)

    def render_variables_section(self, variables: list) -> str:
        """
        Render variables calculation section.

        Args:
            variables: List of variable dictionaries with 'code' field

        Returns:
            Rendered code
        """
        return '\n'.join(var.get('code', '') for var in variables)

    def add_custom_filter(self, name: str, func: Callable):
        """
        Add a custom Jinja2 filter.

        Args:
            name: Filter name
            func: Filter function

        Example:
            >>> manager = TemplateManager()
            >>> manager.add_custom_filter('upper', str.upper)
        """
        self.env.filters[name] = func

    @staticmethod
    def _indent_filter(text: str, spaces: int = 4) -> str:
        """
        Indent text by specified number of spaces.

        Args:
            text: Text to indent
            spaces: Number of spaces

        Returns:
            Indented text
        """
        indent = ' ' * spaces
        lines = text.split('\n')
        return '\n'.join(indent + line if line.strip() else line for line in lines)

    @staticmethod
    def _to_python_type_filter(pine_type: str) -> str:
        """
        Convert Pine Script type to Python type hint.

        Args:
            pine_type: Pine type string

        Returns:
            Python type hint
        """
        type_map = {
            'int': 'int',
            'float': 'float',
            'bool': 'bool',
            'string': 'str',
            'color': 'str',
            'array<float>': 'List[float]',
            'array<int>': 'List[int]',
        }

        return type_map.get(pine_type, 'Any')
