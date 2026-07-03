"""
Dummy Rule

Reference implementation of the BaseRule contract.

This rule always evaluates to True and exists solely as a
minimal example for implementing future market rules.
"""

from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class DummyRule(BaseRule):
    """
    Minimal BaseRule implementation.

    Intended for architecture validation and developer reference.
    """

    def evaluate(self, context: StrategyContext) -> bool:
        """
        Always returns True.

        Args:
            context: Immutable strategy context.

        Returns:
            True
        """
        return True
