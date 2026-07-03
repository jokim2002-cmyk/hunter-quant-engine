"""
Tests for BOSBuilder.
"""

from src.models.bos_point import BOSType
from src.models.swing_point import SwingPointType
from tests.builders.models.bos_builder import BOSBuilder
from tests.builders.models.swing_point_builder import SwingPointBuilder


def test_builds_default_bullish_bos():
    bos = BOSBuilder().build()

    assert bos.bos_type == BOSType.BULLISH
    assert bos.break_price == 100.0
    assert bos.broken_swing.is_swing_high()


def test_builds_bearish_bos():
    bos = BOSBuilder().bearish().build()

    assert bos.bos_type == BOSType.BEARISH


def test_accepts_custom_broken_swing():
    swing = (
        SwingPointBuilder()
        .swing_low()
        .at_price(85.0)
        .build()
    )

    bos = (
        BOSBuilder()
        .with_broken_swing(swing)
        .build()
    )

    assert bos.broken_swing == swing
    assert bos.broken_swing.swing_type == SwingPointType.SWING_LOW


def test_overrides_values():
    bos = (
        BOSBuilder()
        .bearish()
        .at_index(10)
        .at_price(250.5)
        .build()
    )

    assert bos.index == 10
    assert bos.break_price == 250.5
    assert bos.bos_type == BOSType.BEARISH
