"""
Equal High Point Model

This module defines equal high liquidity areas.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from src.models.swing_point import SwingPoint


@dataclass(frozen=True)
class EqualHighPoint:
    index: int
    timestamp: datetime
    price: float
    source_swings: List[SwingPoint]

    def swing_count(self) -> int:
        return len(self.source_swings)

    def is_valid(self) -> bool:
        return self.swing_count() >= 2
