"""
Default Strategy Context Factory

Builds StrategyContext snapshots from walk-forward market data.
"""

from datetime import datetime

from src.engines.bos_engine import BOSEngine
from src.engines.choch_engine import CHOCHEngine
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

    Builds context with candles, metadata, market structure, BOS, and CHOCH.
    Other detection event collections remain empty until further integration.
    """

    def __init__(
        self,
        swing_detection_engine: SwingDetectionEngine | None = None,
        market_structure_builder: MarketStructureBuilder | None = None,
        bos_engine: BOSEngine | None = None,
        choch_engine: CHOCHEngine | None = None,
    ):
        self._swing_detection_engine = (
            swing_detection_engine or SwingDetectionEngine()
        )
        self._market_structure_builder = (
            market_structure_builder or MarketStructureBuilder()
        )
        self._bos_engine = bos_engine or BOSEngine()
        self._choch_engine = choch_engine or CHOCHEngine()

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
            Immutable StrategyContext with detected market structure, BOS, and CHOCH.
        """
        candle_list = list(candles)

        swing_points = self._swing_detection_engine.detect_swings(
            candle_list,
        )
        market_structure_points = self._market_structure_builder.build(
            swing_points,
        )
        bos_events = self._bos_engine.detect_bos(
            candles=candle_list,
            market_structure_points=market_structure_points,
        )
        choch_events = self._choch_engine.detect_choch(
            candles=candle_list,
            market_structure_points=market_structure_points,
        )

        return StrategyContext(
            symbol=symbol,
            timeframe=timeframe,
            analysis_time=analysis_time,
            candles=candles,
            market_structure_points=tuple(market_structure_points),
            bos_events=tuple(bos_events),
            choch_events=tuple(choch_events),
            liquidity_points=(),
            equal_high_points=(),
            equal_low_points=(),
            liquidity_clusters=(),
            liquidity_sweeps=(),
            fair_value_gaps=(),
            order_blocks=(),
        )
