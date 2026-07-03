"""
Liquidity Sweep Builder

Test builder for creating LiquiditySweep objects.
"""

from src.models.liquidity_sweep import LiquiditySweep
from src.models.liquidity_sweep_type import LiquiditySweepType


class LiquiditySweepBuilder:
    """
    Builder for LiquiditySweep test objects.
    """

    def __init__(self):
        self._candle_index = 10
        self._liquidity_index = 5
        self._sweep_price = 101.0
        self._liquidity_price = 100.0
        self._break_distance = 1.0
        self._reclaimed = True
        self._sweep_type = LiquiditySweepType.HIGH
        self._created_at = 10

    def buy_side(self):
        self._sweep_type = LiquiditySweepType.HIGH
        return self

    def sell_side(self):
        self._sweep_type = LiquiditySweepType.LOW
        return self

    def reclaimed(self):
        self._reclaimed = True
        return self

    def not_reclaimed(self):
        self._reclaimed = False
        return self

    def at_candle(self, index: int):
        self._candle_index = index
        return self

    def with_liquidity_index(self, index: int):
        self._liquidity_index = index
        return self

    def at_sweep_price(self, price: float):
        self._sweep_price = price
        return self

    def at_liquidity_price(self, price: float):
        self._liquidity_price = price
        return self

    def with_break_distance(self, distance: float):
        self._break_distance = distance
        return self

    def created_at(self, index: int):
        self._created_at = index
        return self

    def build(self) -> LiquiditySweep:
        return LiquiditySweep(
            candle_index=self._candle_index,
            liquidity_index=self._liquidity_index,
            sweep_price=self._sweep_price,
            liquidity_price=self._liquidity_price,
            break_distance=self._break_distance,
            reclaimed=self._reclaimed,
            sweep_type=self._sweep_type,
            created_at=self._created_at,
        )
