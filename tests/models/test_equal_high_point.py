from datetime import datetime, timedelta

from src.models.equal_high_point import EqualHighPoint
from src.models.swing_point import SwingPoint, SwingPointType


def make_swing_high(index, price):
    return SwingPoint(
        index=index,
        timestamp=datetime(2026, 1, 1, 9, 15) + timedelta(minutes=5 * index),
        price=price,
        swing_type=SwingPointType.SWING_HIGH,
    )


def test_equal_high_point_is_valid_with_two_swings():
    swings = [
        make_swing_high(1, 110.0),
        make_swing_high(3, 110.2),
    ]

    equal_high = EqualHighPoint(
        index=3,
        timestamp=swings[-1].timestamp,
        price=110.1,
        source_swings=swings,
    )

    assert equal_high.swing_count() == 2
    assert equal_high.is_valid() is True


def test_equal_high_point_is_not_valid_with_one_swing():
    swings = [make_swing_high(1, 110.0)]

    equal_high = EqualHighPoint(
        index=1,
        timestamp=swings[0].timestamp,
        price=110.0,
        source_swings=swings,
    )

    assert equal_high.swing_count() == 1
    assert equal_high.is_valid() is False


def test_equal_high_point_keeps_source_swings():
    swings = [
        make_swing_high(1, 110.0),
        make_swing_high(3, 110.2),
    ]

    equal_high = EqualHighPoint(
        index=3,
        timestamp=swings[-1].timestamp,
        price=110.1,
        source_swings=swings,
    )

    assert equal_high.source_swings == swings
