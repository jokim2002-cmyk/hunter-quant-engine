"""
Sell Side Sweep Rule

Returns all sell-side liquidity sweep events
from the current StrategyContext.
"""

from src.models.liquidity_sweep import LiquiditySweep
from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class SellSideSweepRule(BaseRule[LiquiditySweep]):
    """
    Filters sell-side liquidity sweep events.
    """

    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[LiquiditySweep, ...]:
        """
        Return all sell-side liquidity sweep events.

        Args:
            context: Immutable strategy context.

        Returns:
            Tuple of sell-side liquidity sweep events.
        """
        return tuple(
            sweep
            for sweep in context.liquidity_sweeps
            if sweep.is_sell_side()
        )
