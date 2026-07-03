"""
Tests for SwingPointBuilder.
"""

from datetime import datetime

from src.models.swing_point import SwingPointType
from tests.builders.models.swing_point_builder import SwingPointBuilder


def test_builds_default_swing_point():
    swing = SwingPointBuilder().build()

    assert swing.index == 1
    assert swing.timestamp == datetime(2026, 1, 1)
    assert swing.price == 100.0
    assert swing.swing_type == SwingPointType.SWING_HIGH


def test_builds_swing_low():
    swing = SwingPointBuilder().swing_low().build()

    assert swing.swing_type == SwingPointType.SWING_LOW


def test_overrides_swing_point_values():
    timestamp = datetime(2026, 7, 4)

    swing = (
        SwingPointBuilder()
        .at_index(10)
        .at_timestamp(timestamp)
        .at_price(250.5)
        .swing_low()
        .build()
    )

    assert swing.index == 10
    assert swing.timestamp == timestamp
    assert swing.price == 250.5
    assert swing.swing_type == SwingPointType.SWING_LOW
