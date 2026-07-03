"""
Strategy Context

Immutable snapshot of market information consumed by strategies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from src.models.bos_point import BOSPoint
from src.models.candle import Candle
from src.models.choch_point import CHOCHPoint
from src.models.equal_high_point import EqualHighPoint
from src.models.equal_low_point import EqualLowPoint
from src.models.fair_value_gap import FairValueGap
from src.models.liquidity_cluster import LiquidityCluster
from src.models.liquidity_point import LiquidityPoint
from src.models.liquidity_sweep import LiquiditySweep
from src.models.market_structure import MarketStructurePoint
from src.models.order_block import OrderBlock


@dataclass(frozen=True)
class StrategyContext:
    symbol: str
    timeframe: str
    analysis_time: datetime

    candles: Tuple[Candle, ...]
    market_structure_points: Tuple[MarketStructurePoint, ...]

    bos_events: Tuple[BOSPoint, ...]
    choch_events: Tuple[CHOCHPoint, ...]

    liquidity_points: Tuple[LiquidityPoint, ...]
    equal_high_points: Tuple[EqualHighPoint, ...]
    equal_low_points: Tuple[EqualLowPoint, ...]

    liquidity_clusters: Tuple[LiquidityCluster, ...]
    liquidity_sweeps: Tuple[LiquiditySweep, ...]

    fair_value_gaps: Tuple[FairValueGap, ...]
    order_blocks: Tuple[OrderBlock, ...]
