"""
Import Manager for Python Code Generation

Tracks required imports based on indicators and features used,
generates optimized import statements.
"""

from typing import Dict, List, Set
from dataclasses import dataclass, field


@dataclass
class ImportStatement:
    """Represents a Python import statement."""
    module: str
    items: List[str] = field(default_factory=list)
    alias: str = ""

    def to_string(self) -> str:
        """Convert to Python import statement."""
        if self.items:
            items_str = ', '.join(self.items)
            return f"from {self.module} import {items_str}"
        elif self.alias:
            return f"import {self.module} as {self.alias}"
        else:
            return f"import {self.module}"


class ImportManager:
    """
    Manages import statements for generated Python code.

    Tracks required imports based on indicators used, array operations,
    math functions, etc., and generates optimized import blocks.

    Example:
        >>> manager = ImportManager()
        >>> manager.add_indicator('ta.sma')
        >>> manager.add_indicator('ta.ema')
        >>> manager.add_module('typing', ['Dict', 'Optional'])
        >>> imports = manager.generate_import_block()
        >>> 'import pandas as pd' in imports
        True
    """

    def __init__(self):
        """Initialize import manager."""
        # Standard imports that are always needed
        self.base_imports = [
            ImportStatement('pandas', alias='pd'),
            ImportStatement('numpy', alias='np'),
            ImportStatement('typing', items=['Dict', 'List', 'Optional']),
        ]

        # Additional imports based on usage
        self.additional_imports: Dict[str, ImportStatement] = {}

        # Track features used
        self.indicators_used: Set[str] = set()
        self.has_math_operations = False
        self.has_datetime_operations = False

    def add_indicator(self, indicator_name: str) -> None:
        """
        Add an indicator, automatically managing required imports.

        Args:
            indicator_name: Full indicator name (e.g., 'ta.sma', 'ta.ema')

        Example:
            >>> manager = ImportManager()
            >>> manager.add_indicator('ta.sma')
            >>> manager.add_indicator('ta.rsi')
        """
        self.indicators_used.add(indicator_name)

        # All indicators require IndicatorMapper
        if 'indicator_mapper' not in self.additional_imports:
            self.additional_imports['indicator_mapper'] = ImportStatement(
                'converter.indicator_mapper',
                items=['IndicatorMapper']
            )

    def add_module(self, module: str, items: List[str] = None, alias: str = "") -> None:
        """
        Add a custom module import.

        Args:
            module: Module name (e.g., 'math', 'datetime')
            items: Specific items to import (e.g., ['sqrt', 'pow'])
            alias: Module alias (e.g., 'pd' for pandas)

        Example:
            >>> manager = ImportManager()
            >>> manager.add_module('math', ['sqrt', 'log'])
            >>> manager.add_module('datetime', alias='dt')
        """
        if module in self.additional_imports:
            # Merge with existing
            existing = self.additional_imports[module]
            if items:
                existing.items.extend(items)
                # Remove duplicates
                existing.items = list(set(existing.items))
        else:
            self.additional_imports[module] = ImportStatement(
                module,
                items=items or [],
                alias=alias
            )

    def add_math_operations(self) -> None:
        """Mark that math operations are used."""
        self.has_math_operations = True

    def add_datetime_operations(self) -> None:
        """Mark that datetime operations are used."""
        self.has_datetime_operations = True
        self.add_module('datetime', alias='dt')

    def generate_import_block(self) -> str:
        """
        Generate complete import block for Python code.

        Returns:
            Multi-line string of import statements

        Example:
            >>> manager = ImportManager()
            >>> manager.add_indicator('ta.sma')
            >>> imports = manager.generate_import_block()
            >>> 'import pandas as pd' in imports
            True
            >>> 'from converter.indicator_mapper import IndicatorMapper' in imports
            True
        """
        all_imports = []

        # Add base imports
        for imp in self.base_imports:
            all_imports.append(imp.to_string())

        # Add additional imports (sorted for consistency)
        for module in sorted(self.additional_imports.keys()):
            imp = self.additional_imports[module]
            all_imports.append(imp.to_string())

        return '\n'.join(all_imports)

    def get_required_packages(self) -> List[str]:
        """
        Get list of required packages for pip install.

        Returns:
            List of package names

        Example:
            >>> manager = ImportManager()
            >>> manager.add_indicator('ta.sma')
            >>> packages = manager.get_required_packages()
            >>> 'pandas' in packages
            True
            >>> 'numpy' in packages
            True
        """
        packages = ['pandas', 'numpy']

        # Add indicator-related packages if used
        if self.indicators_used:
            # IndicatorMapper uses pandas_ta internally
            packages.append('pandas-ta')

        return packages

    def has_indicators(self) -> bool:
        """Check if any indicators are used."""
        return len(self.indicators_used) > 0

    def get_indicators_summary(self) -> str:
        """
        Get summary of indicators used.

        Returns:
            Comma-separated string of indicator names

        Example:
            >>> manager = ImportManager()
            >>> manager.add_indicator('ta.sma')
            >>> manager.add_indicator('ta.ema')
            >>> manager.get_indicators_summary()
            'ta.ema, ta.sma'
        """
        return ', '.join(sorted(self.indicators_used))
