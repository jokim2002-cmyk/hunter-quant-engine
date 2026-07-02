"""
Liquidity Point Model

This module defines buy-side and sell-side liquidity points.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.models.swing_point import SwingPoint


class LiquidityType(Enum):
    BUY_SIDE = "buy_side"
    SELL_SIDE = "sell_side"


@dataclass(frozen=True)
class LiquidityPoint:
    index: int
    timestamp: datetime
    price: float
    liquidity_type: LiquidityType
    source_swing: SwingPoint

    def is_buy_side(self) -> bool:
        return self.liquidity_type == LiquidityType.BUY_SIDE

    def is_sell_side(self) -> bool:
        return self.liquidity_type == LiquidityType.SELL_SIDE
