from datetime import datetime, timedelta

from src.engines.market_structure_builder import MarketStructureBuilder
from src.models.market_structure import MarketStructureType
from src.models.swing_point import SwingPoint, SwingPointType


def make_swing_point(index, price, swing_type):
    return SwingPoint(
        index=index,
        timestamp=datetime(2026, 1, 1, 9, 15) + timedelta(minutes=5 * index),
        price=price,
        swing_type=swing_type,
    )


def test_market_structure_builder_identifies_highs_and_lows():
    swings = [
        make_swing_point(1, 100.0, SwingPointType.SWING_HIGH),
        make_swing_point(2, 90.0, SwingPointType.SWING_LOW),
        make_swing_point(3, 110.0, SwingPointType.SWING_HIGH),
        make_swing_point(4, 95.0, SwingPointType.SWING_LOW),
        make_swing_point(5, 105.0, SwingPointType.SWING_HIGH),
        make_swing_point(6, 85.0, SwingPointType.SWING_LOW),
    ]

    builder = MarketStructureBuilder()
    result = builder.build(swings)

    assert len(result) == 6
    assert [point.structure_type for point in result] == [
        MarketStructureType.HIGHER_HIGH,
        MarketStructureType.HIGHER_LOW,
        MarketStructureType.HIGHER_HIGH,
        MarketStructureType.HIGHER_LOW,
        MarketStructureType.LOWER_HIGH,
        MarketStructureType.LOWER_LOW,
    ]


def test_market_structure_builder_keeps_original_swing_point():
    swing = make_swing_point(1, 100.0, SwingPointType.SWING_HIGH)

    builder = MarketStructureBuilder()
    result = builder.build([swing])

    assert result[0].swing_point == swing


def test_market_structure_builder_returns_empty_list_for_no_swings():
    builder = MarketStructureBuilder()

    result = builder.build([])

    assert result == []
