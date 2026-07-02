"""
Break of Structure (BOS) Model
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.models.swing_point import SwingPoint


class BOSType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True)
class BOSPoint:
    index: int
    timestamp: datetime
    break_price: float
    bos_type: BOSType
    broken_swing: SwingPoint

    def is_bullish(self) -> bool:
        return self.bos_type == BOSType.BULLISH

    def is_bearish(self) -> bool:
        return self.bos_type == BOSType.BEARISH
