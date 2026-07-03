"""
Base Rule Contract

Defines the abstract contract for all reusable strategy rules.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.strategy.strategy_context import StrategyContext


class BaseRule(ABC):
    """
    Base contract for all strategy rules.

    Rules evaluate immutable StrategyContext snapshots and return
    matching immutable market facts.

    Rules do not:
    - create trade signals
    - execute trades
    - mutate context
    - store state
    """

    @abstractmethod
    def evaluate(self, context: StrategyContext) -> tuple[Any, ...]:
        """
        Evaluate the rule against a StrategyContext.

        Args:
            context: Immutable market snapshot.

        Returns:
            Tuple containing all matching immutable market facts.
            Returns an empty tuple when no match exists.
        """
        raise NotImplementedError
