"""
Order Block Model

Represents an immutable order block market event.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.models.order_block_type import OrderBlockType


@dataclass(frozen=True)
class OrderBlock:
    candle_index: int
    high: float
    low: float
    open: float
    close: float
    order_block_type: OrderBlockType
    created_at: datetime
    mitigated: bool = False
    mitigated_at: Optional[datetime] = None

    def is_bullish(self) -> bool:
        """
        Return True when the order block is bullish.
        """
        return self.order_block_type == OrderBlockType.BULLISH

    def is_bearish(self) -> bool:
        """
        Return True when the order block is bearish.
        """
        return self.order_block_type == OrderBlockType.BEARISH
