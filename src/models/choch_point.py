"""
Change of Character (CHOCH) Model
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.models.swing_point import SwingPoint


class CHOCHType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True)
class CHOCHPoint:
    index: int
    timestamp: datetime
    break_price: float
    choch_type: CHOCHType
    broken_swing: SwingPoint

    def is_bullish(self) -> bool:
        return self.choch_type == CHOCHType.BULLISH

    def is_bearish(self) -> bool:
        return self.choch_type == CHOCHType.BEARISH
