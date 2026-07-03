"""
Bullish CHOCH Rule

Returns all bullish Change of Character (CHOCH) events
from the current StrategyContext.
"""

from src.models.choch_point import CHOCHPoint
from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class BullishCHOCHRule(BaseRule[CHOCHPoint]):
    """
    Filters bullish CHOCH events.
    """

    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[CHOCHPoint, ...]:
        """
        Return all bullish CHOCH events.
        """
        return tuple(
            choch
            for choch in context.choch_events
            if choch.is_bullish()
        )
