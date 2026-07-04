"""
Default Strategy Context Factory

Builds StrategyContext snapshots from walk-forward market data.
"""

from datetime import datetime

from src.engines.market_structure_builder import MarketStructureBuilder
from src.engines.swing_detection_engine import SwingDetectionEngine
from src.models.candle import Candle
from src.strategy.context_factories.base_strategy_context_factory import (
    BaseStrategyContextFactory,
)
from src.strategy.strategy_context import StrategyContext


class DefaultStrategyContextFactory(BaseStrategyContextFactory):
    """
    Default StrategyContext factory.

    Builds context with candles, metadata, and detected market structure points.
    Other detection event collections remain empty until further integration.
    """

    def __init__(
        self,
        swing_detection_engine: SwingDetectionEngine | None = None,
        market_structure_builder: MarketStructureBuilder | None = None,
    ):
        self._swing_detection_engine = (
            swing_detection_engine or SwingDetectionEngine()
        )
        self._market_structure_builder = (
            market_structure_builder or MarketStructureBuilder()
        )

    def create(
        self,
        symbol: str,
        timeframe: str,
        analysis_time: datetime,
        candles: tuple[Candle, ...],
    ) -> StrategyContext:
        """
        Create a StrategyContext snapshot.

        Args:
            symbol: Market symbol.
            timeframe: Market timeframe.
            analysis_time: Current analysis timestamp.
            candles: Walk-forward candles available at analysis time.

        Returns:
            Immutable StrategyContext with detected market structure points.
        """
        swing_points = self._swing_detection_engine.detect_swings(
            list(candles),
        )
        market_structure_points = self._market_structure_builder.build(
            swing_points,
        )

        return StrategyContext(
            symbol=symbol,
            timeframe=timeframe,
            analysis_time=analysis_time,
            candles=candles,
            market_structure_points=tuple(market_structure_points),
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
