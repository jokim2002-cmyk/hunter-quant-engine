from datetime import datetime

import pytest

from src.models.swing_point import SwingPoint, SwingPointType


def test_swing_point_high_identification():
    swing_point = SwingPoint(
        index=5,
        timestamp=datetime(2026, 1, 1, 9, 30),
        price=105.5,
        swing_type=SwingPointType.SWING_HIGH,
    )

    assert swing_point.is_swing_high() is True
    assert swing_point.is_swing_low() is False


def test_swing_point_low_identification():
    swing_point = SwingPoint(
        index=8,
        timestamp=datetime(2026, 1, 1, 9, 45),
        price=98.25,
        swing_type=SwingPointType.SWING_LOW,
    )

    assert swing_point.is_swing_low() is True
    assert swing_point.is_swing_high() is False


def test_swing_point_is_immutable():
    swing_point = SwingPoint(
        index=5,
        timestamp=datetime(2026, 1, 1, 9, 30),
        price=105.5,
        swing_type=SwingPointType.SWING_HIGH,
    )

    with pytest.raises(Exception):
        swing_point.price = 110.0