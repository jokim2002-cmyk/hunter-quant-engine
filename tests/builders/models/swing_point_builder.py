"""
Swing Point Builder

Test builder for creating SwingPoint objects.
"""

from datetime import datetime

from src.models.swing_point import SwingPoint, SwingPointType
from tests.builders.common.defaults import DEFAULT_TIMESTAMP


class SwingPointBuilder:
    """
    Builder for SwingPoint test objects.
    """

    def __init__(self):
        self._index = 1
        self._timestamp = DEFAULT_TIMESTAMP
        self._price = 100.0
        self._swing_type = SwingPointType.SWING_HIGH

    def at_index(self, index: int):
        self._index = index
        return self

    def at_timestamp(self, timestamp: datetime):
        self._timestamp = timestamp
        return self

    def at_price(self, price: float):
        self._price = price
        return self

    def swing_high(self):
        self._swing_type = SwingPointType.SWING_HIGH
        return self

    def swing_low(self):
        self._swing_type = SwingPointType.SWING_LOW
        return self

    def build(self) -> SwingPoint:
        return SwingPoint(
            index=self._index,
            timestamp=self._timestamp,
            price=self._price,
            swing_type=self._swing_type,
        )
