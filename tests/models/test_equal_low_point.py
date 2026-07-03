from datetime import datetime, timedelta

from src.models.equal_low_point import EqualLowPoint
from src.models.swing_point import SwingPoint, SwingPointType


def make_swing_low(index, price):
    return SwingPoint(
        index=index,
        timestamp=datetime(2026, 1, 1, 9, 15) + timedelta(minutes=5 * index),
        price=price,
        swing_type=SwingPointType.SWING_LOW,
    )


def test_equal_low_point_is_valid_with_two_swings():
    swings = [
        make_swing_low(1, 90.0),
        make_swing_low(3, 90.1),
    ]

    equal_low = EqualLowPoint(
        index=3,
        timestamp=swings[-1].timestamp,
        price=90.05,
        source_swings=swings,
    )

    assert equal_low.swing_count() == 2
    assert equal_low.is_valid()


def test_equal_low_point_is_not_valid_with_one_swing():
    swings = [make_swing_low(1, 90.0)]

    equal_low = EqualLowPoint(
        index=1,
        timestamp=swings[0].timestamp,
        price=90.0,
        source_swings=swings,
    )

    assert equal_low.swing_count() == 1
    assert not equal_low.is_valid()


def test_equal_low_point_keeps_source_swings():
    swings = [
        make_swing_low(1, 90.0),
        make_swing_low(3, 90.1),
    ]

    equal_low = EqualLowPoint(
        index=3,
        timestamp=swings[-1].timestamp,
        price=90.05,
        source_swings=swings,
    )

    assert equal_low.source_swings == swings
