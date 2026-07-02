from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from src.models.market_structure import MarketStructurePoint, MarketStructureType
from src.models.swing_point import SwingPoint, SwingPointType


def create_swing_point():
    return SwingPoint(
        index=5,
        timestamp=datetime(2026, 1, 1, 9, 30),
        price=110.0,
        swing_type=SwingPointType.SWING_HIGH,
    )


def test_market_structure_higher_high():
    point = MarketStructurePoint(create_swing_point(), MarketStructureType.HIGHER_HIGH)

    assert point.is_higher_high() is True
    assert point.is_lower_high() is False


def test_market_structure_lower_high():
    point = MarketStructurePoint(create_swing_point(), MarketStructureType.LOWER_HIGH)

    assert point.is_lower_high() is True
    assert point.is_higher_high() is False


def test_market_structure_higher_low():
    point = MarketStructurePoint(create_swing_point(), MarketStructureType.HIGHER_LOW)

    assert point.is_higher_low() is True
    assert point.is_lower_low() is False


def test_market_structure_lower_low():
    point = MarketStructurePoint(create_swing_point(), MarketStructureType.LOWER_LOW)

    assert point.is_lower_low() is True
    assert point.is_higher_low() is False


def test_market_structure_is_immutable():
    point = MarketStructurePoint(create_swing_point(), MarketStructureType.HIGHER_HIGH)

    with pytest.raises(FrozenInstanceError):
        point.structure_type = MarketStructureType.LOWER_HIGH
