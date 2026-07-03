"""
Buy Side Sweep Rule

Returns all buy-side liquidity sweep events
from the current StrategyContext.
"""

from src.models.liquidity_sweep import LiquiditySweep
from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class BuySideSweepRule(BaseRule[LiquiditySweep]):
    """
    Filters buy-side liquidity sweep events.
    """

    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[LiquiditySweep, ...]:
        """
        Return all buy-side liquidity sweep events.

        Args:
            context: Immutable strategy context.

        Returns:
            Tuple of buy-side liquidity sweep events.
        """
        return tuple(
            sweep
            for sweep in context.liquidity_sweeps
            if sweep.is_buy_side()
        )
