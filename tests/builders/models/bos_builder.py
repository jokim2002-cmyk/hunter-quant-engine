"""
BOS Point Builder

Test builder for creating BOSPoint objects.
"""

from src.models.bos_point import BOSPoint, BOSType
from src.models.swing_point import SwingPoint, SwingPointType
from tests.builders.common.defaults import DEFAULT_TIMESTAMP


class BOSBuilder:
    """
    Builder for BOSPoint test objects.
    """

    def __init__(self):
        self._index = 1
        self._timestamp = DEFAULT_TIMESTAMP
        self._break_price = 100.0
        self._bos_type = BOSType.BULLISH

        self._broken_swing = SwingPoint(
            index=0,
            timestamp=DEFAULT_TIMESTAMP,
            price=99.0,
            swing_type=SwingPointType.SWING_HIGH,
        )

    def bullish(self):
        self._bos_type = BOSType.BULLISH
        return self

    def bearish(self):
        self._bos_type = BOSType.BEARISH
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

    def build(self) -> BOSPoint:
        return BOSPoint(
            index=self._index,
            timestamp=self._timestamp,
            break_price=self._break_price,
            bos_type=self._bos_type,
            broken_swing=self._broken_swing,
        )
