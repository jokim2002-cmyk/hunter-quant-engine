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