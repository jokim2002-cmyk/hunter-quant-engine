"""
CHOCH Point Builder

Test builder for creating CHOCHPoint objects.
"""

from src.models.choch_point import CHOCHPoint, CHOCHType
from src.models.swing_point import SwingPoint, SwingPointType
from tests.builders.common.defaults import DEFAULT_TIMESTAMP


class CHOCHBuilder:
    """
    Builder for CHOCHPoint test objects.
    """

    def __init__(self):
        self._index = 1
        self._timestamp = DEFAULT_TIMESTAMP
        self._break_price = 100.0
        self._choch_type = CHOCHType.BULLISH

        self._broken_swing = SwingPoint(
            index=0,
            timestamp=DEFAULT_TIMESTAMP,
            price=99.0,
            swing_type=SwingPointType.SWING_HIGH,
        )

    def bullish(self):
        self._choch_type = CHOCHType.BULLISH
        return self

    def bearish(self):
        self._choch_type = CHOCHType.BEARISH
        return self

    def at_index(self, index: int):
        self._index = index
        return self

    def at_price(self, price: float):
        self._break_price = price
        return self

    def at_timestamp(self, timestamp):
        self._timestamp = timestamp
        return self

    def with_broken_swing(self, swing: SwingPoint):
        self._broken_swing = swing
        return self

    def build(self) -> CHOCHPoint:
        return CHOCHPoint(
            index=self._index,
            timestamp=self._timestamp,
            break_price=self._break_price,
            choch_type=self._choch_type,
            broken_swing=self._broken_swing,
        )
