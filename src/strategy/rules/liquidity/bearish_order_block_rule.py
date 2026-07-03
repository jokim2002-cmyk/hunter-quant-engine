"""
Bearish Order Block Rule

Returns all bearish Order Block events
from the current StrategyContext.
"""

from src.models.order_block import OrderBlock
from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class BearishOrderBlockRule(BaseRule[OrderBlock]):
    """
    Filters bearish Order Block events.
    """

    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[OrderBlock, ...]:
        """
        Return all bearish Order Block events.

        Args:
            context: Immutable strategy context.

        Returns:
            Tuple of bearish Order Block events.
        """
        return tuple(
            order_block
            for order_block in context.order_blocks
            if order_block.is_bearish()
        )
