from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from src.models.choch_point import CHOCHPoint, CHOCHType
from src.models.swing_point import SwingPoint, SwingPointType


def test_choch_point_bullish_identification():
    broken_swing = SwingPoint(
        index=3,
        timestamp=datetime(2026, 1, 1, 9, 30),
        price=110.0,
        swing_type=SwingPointType.SWING_HIGH,
    )

    choch_point = CHOCHPoint(
        index=5,
        timestamp=datetime(2026, 1, 1, 9, 40),
        break_price=111.0,
        choch_type=CHOCHType.BULLISH,
        broken_swing=broken_swing,
    )

    assert choch_point.is_bullish() is True
    assert choch_point.is_bearish() is False


def test_choch_point_bearish_identification():
    broken_swing = SwingPoint(
        index=3,
        timestamp=datetime(2026, 1, 1, 9, 30),
        price=90.0,
        swing_type=SwingPointType.SWING_LOW,
    )

    choch_point = CHOCHPoint(
        index=5,
        timestamp=datetime(2026, 1, 1, 9, 40),
        break_price=89.0,
        choch_type=CHOCHType.BEARISH,
        broken_swing=broken_swing,
    )

    assert choch_point.is_bearish() is True
    assert choch_point.is_bullish() is False


def test_choch_point_stores_broken_swing_context():
    broken_swing = SwingPoint(
        index=3,
        timestamp=datetime(2026, 1, 1, 9, 30),
        price=110.0,
        swing_type=SwingPointType.SWING_HIGH,
    )

    choch_point = CHOCHPoint(
        index=5,
        timestamp=datetime(2026, 1, 1, 9, 40),
        break_price=111.0,
        choch_type=CHOCHType.BULLISH,
        broken_swing=broken_swing,
    )

    assert choch_point.broken_swing == broken_swing
    assert choch_point.broken_swing.index == 3
    assert choch_point.broken_swing.price == 110.0
    assert choch_point.broken_swing.is_swing_high() is True


def test_choch_point_is_immutable():
    broken_swing = SwingPoint(
        index=3,
        timestamp=datetime(2026, 1, 1, 9, 30),
        price=110.0,
        swing_type=SwingPointType.SWING_HIGH,
    )

    choch_point = CHOCHPoint(
        index=5,
        timestamp=datetime(2026, 1, 1, 9, 40),
        break_price=111.0,
        choch_type=CHOCHType.BULLISH,
        broken_swing=broken_swing,
    )

    with pytest.raises(FrozenInstanceError):
        choch_point.break_price = 112.0
