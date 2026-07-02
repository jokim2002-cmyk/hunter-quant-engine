"""
Liquidity Engine

Creates liquidity points from market structure.
"""

from typing import List

from src.config.liquidity_config import LiquidityConfig, DEFAULT_LIQUIDITY_CONFIG
from src.models.liquidity_point import LiquidityPoint, LiquidityType
from src.models.market_structure import MarketStructurePoint, MarketStructureType


class LiquidityEngine:
    """
    Creates buy-side and sell-side liquidity points.
    """

    def __init__(
        self,
        config: LiquidityConfig = DEFAULT_LIQUIDITY_CONFIG,
    ) -> None:
        self.config = config

    def detect_liquidity(
        self,
        market_structure_points: List[MarketStructurePoint],
    ) -> List[LiquidityPoint]:

        liquidity_points: List[LiquidityPoint] = []

        if not self.config.enabled:
            return liquidity_points

        for structure_point in market_structure_points:

            if structure_point.structure_type in (
                MarketStructureType.HIGHER_HIGH,
                MarketStructureType.LOWER_HIGH,
            ):
                liquidity_type = LiquidityType.BUY_SIDE

            elif structure_point.structure_type in (
                MarketStructureType.HIGHER_LOW,
                MarketStructureType.LOWER_LOW,
            ):
                liquidity_type = LiquidityType.SELL_SIDE

            else:
                raise ValueError("Invalid market structure type.")

            swing = structure_point.swing_point

            liquidity_points.append(
                LiquidityPoint(
                    index=swing.index,
                    timestamp=swing.timestamp,
                    price=swing.price,
                    liquidity_type=liquidity_type,
                    source_swing=swing,
                )
            )

        return liquidity_points
