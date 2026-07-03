"""
Bearish BOS Rule

Returns all bearish Break of Structure (BOS) events
from the current StrategyContext.
"""

from src.models.bos_point import BOSPoint
from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class BearishBOSRule(BaseRule[BOSPoint]):
    """
    Filters bearish BOS events.
    """

    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[BOSPoint, ...]:
        """
        Return all bearish BOS events.

        Args:
            context: Immutable strategy context.

        Returns:
            Tuple of bearish BOS events.
        """
        return tuple(
            bos
            for bos in context.bos_events
            if bos.is_bearish()
        )
