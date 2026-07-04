"""
Default Strategy Context Factory

Builds minimal StrategyContext snapshots.
"""

from datetime import datetime

from src.models.candle import Candle
from src.strategy.context_factories.base_strategy_context_factory import (
    BaseStrategyContextFactory,
)
from src.strategy.strategy_context import StrategyContext


class DefaultStrategyContextFactory(BaseStrategyContextFactory):
    """
    Default StrategyContext factory.

    Version 1 builds context with candles and metadata only.
    Detection event collections remain empty until detection integration.
    """

    def create(
        self,
        symbol: str,
        timeframe: str,
        analysis_time: datetime,
        candles: tuple[Candle, ...],
    ) -> StrategyContext:
        """
        Create a minimal StrategyContext snapshot.

        Args:
            symbol: Market symbol.
            timeframe: Market timeframe.
            analysis_time: Current analysis timestamp.
            candles: Walk-forward candles available at analysis time.

        Returns:
            Immutable StrategyContext with empty detection event collections.
        """
        return StrategyContext(
            symbol=symbol,
            timeframe=timeframe,
            analysis_time=analysis_time,
            candles=candles,
            market_structure_points=(),
            bos_events=(),
            choch_events=(),
            liquidity_points=(),
            equal_high_points=(),
            equal_low_points=(),
            liquidity_clusters=(),
            liquidity_sweeps=(),
            fair_value_gaps=(),
            order_blocks=(),
        )
