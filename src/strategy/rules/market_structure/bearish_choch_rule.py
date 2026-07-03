"""
Bearish CHOCH Rule

Returns all bearish Change of Character (CHOCH) events
from the current StrategyContext.
"""

from src.models.choch_point import CHOCHPoint
from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class BearishCHOCHRule(BaseRule[CHOCHPoint]):
    """
    Filters bearish CHOCH events.
    """

    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[CHOCHPoint, ...]:
        """
        Return all bearish CHOCH events.

        Args:
            context: Immutable strategy context.

        Returns:
            Tuple of bearish CHOCH events.
        """
        return tuple(
            choch
            for choch in context.choch_events
            if choch.is_bearish()
        )
