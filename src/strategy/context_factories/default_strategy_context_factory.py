"""
Default Strategy Context Factory

Builds StrategyContext snapshots from walk-forward market data.
"""

from datetime import datetime

from src.engines.bos_engine import BOSEngine
from src.engines.choch_engine import CHOCHEngine
from src.engines.equal_level_engine import EqualLevelEngine
from src.engines.fair_value_gap_engine import FairValueGapEngine
from src.engines.liquidity_cluster_engine import LiquidityClusterEngine
from src.engines.liquidity_engine import LiquidityEngine
from src.engines.liquidity_sweep_engine import LiquiditySweepEngine
from src.engines.market_structure_builder import MarketStructureBuilder
from src.engines.swing_detection_engine import SwingDetectionEngine
from src.models.candle import Candle
from src.models.equal_level_type import EqualLevelType
from src.strategy.context_factories.base_strategy_context_factory import (
    BaseStrategyContextFactory,
)
from src.strategy.strategy_context import StrategyContext


class DefaultStrategyContextFactory(BaseStrategyContextFactory):
    """
    Default StrategyContext factory.

    Builds context with candles, metadata, market structure, BOS, CHOCH,
    liquidity points, equal levels, liquidity clusters, liquidity sweeps,
    and fair value gaps.
    Order blocks remain empty until further integration.
    """

    def __init__(
        self,
        swing_detection_engine: SwingDetectionEngine | None = None,
        market_structure_builder: MarketStructureBuilder | None = None,
        bos_engine: BOSEngine | None = None,
        choch_engine: CHOCHEngine | None = None,
        liquidity_engine: LiquidityEngine | None = None,
        equal_level_engine: EqualLevelEngine | None = None,
        liquidity_cluster_engine: LiquidityClusterEngine | None = None,
        liquidity_sweep_engine: LiquiditySweepEngine | None = None,
        fair_value_gap_engine: FairValueGapEngine | None = None,
    ):
        self._swing_detection_engine = (
            swing_detection_engine or SwingDetectionEngine()
        )
        self._market_structure_builder = (
            market_structure_builder or MarketStructureBuilder()
        )
        self._bos_engine = bos_engine or BOSEngine()
        self._choch_engine = choch_engine or CHOCHEngine()
        self._liquidity_engine = liquidity_engine or LiquidityEngine()
        self._equal_level_engine = equal_level_engine or EqualLevelEngine()
        self._liquidity_cluster_engine = (
            liquidity_cluster_engine or LiquidityClusterEngine()
        )
        self._liquidity_sweep_engine = (
            liquidity_sweep_engine or LiquiditySweepEngine()
        )
        self._fair_value_gap_engine = (
            fair_value_gap_engine or FairValueGapEngine()
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
            Immutable StrategyContext with detected market facts.
        """
        candle_list = list(candles)

        fair_value_gaps = self._fair_value_gap_engine.detect(
            candle_list,
        )

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
        liquidity_points = self._liquidity_engine.detect_liquidity(
            market_structure_points=market_structure_points,
        )
        equal_high_points = self._equal_level_engine.detect_equal_levels(
            market_structure_points=market_structure_points,
            level_type=EqualLevelType.HIGH,
        )
        equal_low_points = self._equal_level_engine.detect_equal_levels(
            market_structure_points=market_structure_points,
            level_type=EqualLevelType.LOW,
        )
        liquidity_clusters = self._liquidity_cluster_engine.build_clusters(
            liquidity_points=liquidity_points,
        )
        liquidity_sweeps = self._liquidity_sweep_engine.detect(
            candles=candle_list,
            liquidity_points=liquidity_points,
        )

        return StrategyContext(
            symbol=symbol,
            timeframe=timeframe,
            analysis_time=analysis_time,
            candles=candles,
            market_structure_points=tuple(market_structure_points),
            bos_events=tuple(bos_events),
            choch_events=tuple(choch_events),
            liquidity_points=tuple(liquidity_points),
            equal_high_points=tuple(equal_high_points),
            equal_low_points=tuple(equal_low_points),
            liquidity_clusters=tuple(liquidity_clusters),
            liquidity_sweeps=tuple(liquidity_sweeps),
            fair_value_gaps=tuple(fair_value_gaps),
            order_blocks=(),
        )
