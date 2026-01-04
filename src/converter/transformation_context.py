"""
Transformation Context for Pine Script to Python Conversion

Manages variable scope, built-in mappings, and transformation state during
the expression transformation process.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Set
import logging

logger = logging.getLogger(__name__)


@dataclass
class TransformationContext:
    """
    Context manager for Pine Script to Python transformation.

    Tracks variables, built-in mappings, and scope during the conversion process.
    Each context represents a scope level (global, function, etc.).

    Attributes:
        variables: User-defined variable mappings (pine_name → python_name)
        builtins_map: Built-in Pine variables to Python equivalents
        scope_level: Current nesting level (0 = global)
        indicators_used: Set of indicator names used in expressions
        parent_context: Parent scope context for nested scopes

    Example:
        >>> context = TransformationContext()
        >>> context.add_variable("fast", "self.fast_ema")
        >>> context.get_variable("fast")
        'self.fast_ema'
        >>> context.map_builtin("close")
        'self.close'
    """

    variables: Dict[str, str] = field(default_factory=dict)
    builtins_map: Dict[str, str] = field(default_factory=dict)
    scope_level: int = 0
    indicators_used: Set[str] = field(default_factory=set)
    parent_context: Optional['TransformationContext'] = None

    def __post_init__(self):
        """Initialize default built-in mappings if not provided."""
        if not self.builtins_map:
            self.builtins_map = self._get_default_builtins()

    @staticmethod
    def _get_default_builtins() -> Dict[str, str]:
        """
        Get default Pine built-in variable mappings.

        Returns:
            Dictionary mapping Pine built-ins to Python equivalents
        """
        return {
            # Price data
            'close': 'self.close',
            'open': 'self.open',
            'high': 'self.high',
            'low': 'self.low',
            'volume': 'self.volume',
            'hl2': '(self.high + self.low) / 2',
            'hlc3': '(self.high + self.low + self.close) / 3',
            'ohlc4': '(self.open + self.high + self.low + self.close) / 4',

            # Bar info
            'bar_index': 'len(self.close) - 1',
            'barstate.isfirst': 'len(self.close) == 1',
            'barstate.islast': 'True',  # Always true in backtesting context
            'barstate.isrealtime': 'False',  # Historical backtesting

            # Strategy state
            'strategy.position_size': 'self.position_size',
            'strategy.long': 'strategy.long',
            'strategy.short': 'strategy.short',

            # Constants
            'true': 'True',
            'false': 'False',
            'na': 'np.nan',
        }

    def add_variable(self, pine_name: str, python_name: str) -> None:
        """
        Add a user-defined variable mapping.

        Args:
            pine_name: Variable name in Pine Script
            python_name: Corresponding Python variable name

        Example:
            >>> context.add_variable("fast", "self.fast_ema")
        """
        self.variables[pine_name] = python_name
        logger.debug(f"Added variable: {pine_name} → {python_name}")

    def get_variable(self, pine_name: str) -> Optional[str]:
        """
        Get Python name for a Pine variable.

        Searches current scope and parent scopes.

        Args:
            pine_name: Variable name in Pine Script

        Returns:
            Python variable name, or None if not found

        Example:
            >>> context.get_variable("fast")
            'self.fast_ema'
        """
        # Check current scope
        if pine_name in self.variables:
            return self.variables[pine_name]

        # Check parent scope
        if self.parent_context:
            return self.parent_context.get_variable(pine_name)

        return None

    def is_builtin(self, name: str) -> bool:
        """
        Check if a name is a Pine built-in variable.

        Args:
            name: Variable name to check

        Returns:
            True if name is a built-in

        Example:
            >>> context.is_builtin("close")
            True
            >>> context.is_builtin("my_var")
            False
        """
        return name in self.builtins_map

    def map_builtin(self, name: str) -> str:
        """
        Map a Pine built-in to Python equivalent.

        Args:
            name: Built-in variable name

        Returns:
            Python equivalent expression

        Raises:
            KeyError: If name is not a known built-in

        Example:
            >>> context.map_builtin("close")
            'self.close'
            >>> context.map_builtin("hl2")
            '(self.high + self.low) / 2'
        """
        if name not in self.builtins_map:
            raise KeyError(f"Unknown built-in: {name}")

        return self.builtins_map[name]

    def add_indicator(self, indicator_name: str) -> None:
        """
        Track usage of a Pine indicator function.

        Args:
            indicator_name: Full indicator name (e.g., 'ta.sma', 'ta.ema')

        Example:
            >>> context.add_indicator('ta.sma')
            >>> context.add_indicator('ta.ema')
            >>> context.indicators_used
            {'ta.sma', 'ta.ema'}
        """
        self.indicators_used.add(indicator_name)
        logger.debug(f"Indicator used: {indicator_name}")

    def create_child_context(self) -> 'TransformationContext':
        """
        Create a nested scope context (for functions, blocks).

        Returns:
            New TransformationContext with current as parent

        Example:
            >>> parent = TransformationContext()
            >>> parent.add_variable("x", "self.x")
            >>> child = parent.create_child_context()
            >>> child.get_variable("x")  # Can access parent variables
            'self.x'
            >>> child.scope_level
            1
        """
        return TransformationContext(
            variables={},  # Fresh variable scope
            builtins_map=self.builtins_map,  # Share built-ins
            scope_level=self.scope_level + 1,
            indicators_used=self.indicators_used,  # Share indicator tracking
            parent_context=self
        )

    def merge_from_child(self, child_context: 'TransformationContext') -> None:
        """
        Merge indicators and state from a child context.

        Used when exiting a nested scope to preserve indicator usage.

        Args:
            child_context: Child context to merge from
        """
        self.indicators_used.update(child_context.indicators_used)

    def resolve_name(self, name: str) -> str:
        """
        Resolve a Pine name to Python equivalent.

        Checks in order:
        1. Built-in variables
        2. User-defined variables in current/parent scope
        3. Returns as-is if not found (assume it's valid Python)

        Args:
            name: Pine Script identifier

        Returns:
            Python equivalent expression

        Example:
            >>> context.add_variable("fast", "self.fast_ema")
            >>> context.resolve_name("close")
            'self.close'
            >>> context.resolve_name("fast")
            'self.fast_ema'
            >>> context.resolve_name("unknown")
            'unknown'
        """
        # Check built-ins first
        if self.is_builtin(name):
            return self.map_builtin(name)

        # Check user variables
        var = self.get_variable(name)
        if var:
            return var

        # Unknown - return as-is
        return name

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"TransformationContext("
            f"scope_level={self.scope_level}, "
            f"variables={len(self.variables)}, "
            f"indicators={len(self.indicators_used)})"
        )
