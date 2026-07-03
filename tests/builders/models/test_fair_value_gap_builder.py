"""
Tests for FairValueGapBuilder.
"""

from src.models.fair_value_gap_type import FairValueGapType
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder


def test_builds_bullish_fair_value_gap_by_default():
    fvg = FairValueGapBuilder().build()

    assert fvg.is_bullish()
    assert fvg.direction == FairValueGapType.BULLISH


def test_builds_bearish_fair_value_gap():
    fvg = FairValueGapBuilder().bearish().build()

    assert fvg.is_bearish()
    assert fvg.direction == FairValueGapType.BEARISH


def test_builds_fair_value_gap_with_custom_indexes():
    fvg = (
        FairValueGapBuilder()
        .from_index(20)
        .to_index(22)
        .created_at(22)
        .build()
    )

    assert fvg.start_index == 20
    assert fvg.end_index == 22
    assert fvg.created_at == 22


def test_builds_fair_value_gap_with_custom_prices():
    fvg = (
        FairValueGapBuilder()
        .with_high(110.0)
        .with_low(104.0)
        .build()
    )

    assert fvg.high == 110.0
    assert fvg.low == 104.0


def test_builds_filled_fair_value_gap():
    fvg = FairValueGapBuilder().filled_at(15).build()

    assert fvg.filled is True
    assert fvg.filled_at == 15


def test_builds_unfilled_fair_value_gap():
    fvg = FairValueGapBuilder().filled_at(15).unfilled().build()

    assert fvg.filled is False
    assert fvg.filled_at is None
