"""
Base Rule Contract

Defines the abstract contract for all reusable strategy rules.
"""

from abc import ABC, abstractmethod

from src.strategy.strategy_context import StrategyContext


class BaseRule(ABC):
    """
    Base contract for all strategy rules.

    Rules evaluate immutable StrategyContext snapshots and return
    whether a market condition is present.

    Rules do not:
    - create trade signals
    - execute trades
    - mutate context
    - store state
    """

    @abstractmethod
    def evaluate(self, context: StrategyContext) -> bool:
        """
        Evaluate the rule against a StrategyContext.

        Args:
            context: Immutable market snapshot.

        Returns:
            True if the rule condition is satisfied, otherwise False.
        """
        raise NotImplementedError
