"""
Bullish BOS Rule

Returns all bullish Break of Structure (BOS) events
from the current StrategyContext.
"""

from src.models.bos_point import BOSPoint
from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class BullishBOSRule(BaseRule[BOSPoint]):
    """
    Filters bullish BOS events.
    """

    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[BOSPoint, ...]:
        """
        Return all bullish BOS events.

        Args:
            context: Immutable strategy context.

        Returns:
            Tuple of bullish BOS events.
        """
        return tuple(
            bos
            for bos in context.bos_events
            if bos.is_bullish()
        )
