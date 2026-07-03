"""
Fair Value Gap Model

Represents a detected Fair Value Gap market event.
"""

from dataclasses import dataclass
from typing import Optional

from src.models.fair_value_gap_type import FairValueGapType


@dataclass(frozen=True)
class FairValueGap:
    """
    Immutable model for a Fair Value Gap event.
    """

    start_index: int
    end_index: int
    high: float
    low: float
    direction: FairValueGapType
    created_at: int
    filled: bool = False
    filled_at: Optional[int] = None

    def is_bullish(self) -> bool:
        """
        Return True when this is a bullish Fair Value Gap.
        """
        return self.direction == FairValueGapType.BULLISH

    def is_bearish(self) -> bool:
        """
        Return True when this is a bearish Fair Value Gap.
        """
        return self.direction == FairValueGapType.BEARISH
