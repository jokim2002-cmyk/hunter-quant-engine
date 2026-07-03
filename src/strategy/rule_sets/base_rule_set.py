"""
Base Rule Set Contract

Defines the abstract contract for strategy rule composition.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.strategy.strategy_context import StrategyContext

T = TypeVar("T")


class BaseRuleSet(ABC, Generic[T]):
    """
    Base contract for all strategy rule sets.

    Rule sets evaluate immutable StrategyContext snapshots and return
    immutable typed rule set results.

    Rule sets do not:
    - create trade signals
    - execute trades
    - mutate context
    - store stateful market data
    """

    @abstractmethod
    def evaluate(
        self,
        context: StrategyContext,
    ) -> T:
        """
        Evaluate the rule set against a StrategyContext.

        Args:
            context: Immutable market snapshot.

        Returns:
            Immutable typed rule set result.
        """
        raise NotImplementedError
