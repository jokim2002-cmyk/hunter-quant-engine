"""
Fair Value Gap Builder

Test builder for creating FairValueGap objects.
"""

from src.models.fair_value_gap import FairValueGap
from src.models.fair_value_gap_type import FairValueGapType


class FairValueGapBuilder:
    """
    Builder for FairValueGap test objects.
    """

    def __init__(self):
        self._start_index = 10
        self._end_index = 12
        self._high = 105.0
        self._low = 100.0
        self._direction = FairValueGapType.BULLISH
        self._created_at = 12
        self._filled = False
        self._filled_at = None

    def bullish(self):
        self._direction = FairValueGapType.BULLISH
        return self

    def bearish(self):
        self._direction = FairValueGapType.BEARISH
        return self

    def from_index(self, index: int):
        self._start_index = index
        return self

    def to_index(self, index: int):
        self._end_index = index
        return self

    def with_high(self, price: float):
        self._high = price
        return self

    def with_low(self, price: float):
        self._low = price
        return self

    def created_at(self, index: int):
        self._created_at = index
        return self

    def filled(self):
        self._filled = True
        return self

    def unfilled(self):
        self._filled = False
        self._filled_at = None
        return self

    def filled_at(self, index: int):
        self._filled = True
        self._filled_at = index
        return self

    def build(self) -> FairValueGap:
        return FairValueGap(
            start_index=self._start_index,
            end_index=self._end_index,
            high=self._high,
            low=self._low,
            direction=self._direction,
            created_at=self._created_at,
            filled=self._filled,
            filled_at=self._filled_at,
        )
