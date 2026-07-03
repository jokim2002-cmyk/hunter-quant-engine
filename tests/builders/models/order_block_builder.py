"""
Order Block Builder

Test builder for creating OrderBlock objects.
"""

from datetime import datetime

from src.models.order_block import OrderBlock
from src.models.order_block_type import OrderBlockType


class OrderBlockBuilder:
    """
    Builder for OrderBlock test objects.
    """

    def __init__(self):
        self._candle_index = 10
        self._high = 110.0
        self._low = 100.0
        self._open = 108.0
        self._close = 102.0
        self._order_block_type = OrderBlockType.BULLISH
        self._created_at = datetime(2026, 1, 1)
        self._mitigated = False
        self._mitigated_at = None

    def bullish(self):
        self._order_block_type = OrderBlockType.BULLISH
        return self

    def bearish(self):
        self._order_block_type = OrderBlockType.BEARISH
        return self

    def at_index(self, candle_index: int):
        self._candle_index = candle_index
        return self

    def with_high(self, high: float):
        self._high = high
        return self

    def with_low(self, low: float):
        self._low = low
        return self

    def with_open(self, open_price: float):
        self._open = open_price
        return self

    def with_close(self, close_price: float):
        self._close = close_price
        return self

    def created_at(self, created_at: datetime):
        self._created_at = created_at
        return self

    def mitigated_at(self, mitigated_at: datetime):
        self._mitigated = True
        self._mitigated_at = mitigated_at
        return self

    def unmitigated(self):
        self._mitigated = False
        self._mitigated_at = None
        return self

    def build(self):
        return OrderBlock(
            candle_index=self._candle_index,
            high=self._high,
            low=self._low,
            open=self._open,
            close=self._close,
            order_block_type=self._order_block_type,
            created_at=self._created_at,
            mitigated=self._mitigated,
            mitigated_at=self._mitigated_at,
        )
