"""
Equal Low Point Model

This module defines equal low liquidity areas.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from src.models.swing_point import SwingPoint


@dataclass(frozen=True)
class EqualLowPoint:
    """
    Represents an Equal Low liquidity area.
    """

    index: int
    timestamp: datetime
    price: float
    source_swings: List[SwingPoint]

    def swing_count(self) -> int:
        """
        Returns the number of swing lows in this equal low.
        """
        return len(self.source_swings)

    def is_valid(self) -> bool:
        """
        Equal Low is valid if it contains at least two swing lows.
        """
        return self.swing_count() >= 2
