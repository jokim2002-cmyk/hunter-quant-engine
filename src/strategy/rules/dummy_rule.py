"""
Dummy Rule

Reference implementation of the BaseRule contract.
"""

from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class DummyRule(BaseRule[object]):
    """
    Minimal BaseRule implementation.

    Intended for architecture validation and developer reference.
    """

    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[object, ...]:
        return ()
