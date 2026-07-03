"""
Base Rule Contract

Defines the abstract contract for all reusable strategy rules.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.strategy.strategy_context import StrategyContext

T = TypeVar("T")


class BaseRule(ABC, Generic[T]):
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
    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[T, ...]:
        """
        Evaluate the rule against a StrategyContext.

        Args:
            context: Immutable market snapshot.

        Returns:
            Tuple containing all matching immutable market facts.
            Returns an empty tuple when no match exists.
        """
        raise NotImplementedError
