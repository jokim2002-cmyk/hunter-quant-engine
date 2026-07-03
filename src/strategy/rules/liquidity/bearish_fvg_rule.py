"""
Bearish FVG Rule

Returns all bearish Fair Value Gap events
from the current StrategyContext.
"""

from src.models.fair_value_gap import FairValueGap
from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class BearishFVGRule(BaseRule[FairValueGap]):
    """
    Filters bearish Fair Value Gap events.
    """

    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[FairValueGap, ...]:
        """
        Return all bearish Fair Value Gap events.

        Args:
            context: Immutable strategy context.

        Returns:
            Tuple of bearish Fair Value Gap events.
        """
        return tuple(
            fvg
            for fvg in context.fair_value_gaps
            if fvg.is_bearish()
        )
