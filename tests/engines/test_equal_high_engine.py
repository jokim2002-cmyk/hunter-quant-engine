from datetime import datetime, timedelta

from src.config.equal_high_config import EqualHighConfig
from src.engines.equal_high_engine import EqualHighEngine
from src.models.market_structure import MarketStructurePoint, MarketStructureType
from src.models.swing_point import SwingPoint, SwingPointType


def make_swing(index, price, swing_type):
    return SwingPoint(
        index=index,
        timestamp=datetime(2026, 1, 1, 9, 15) + timedelta(minutes=5 * index),
        price=price,
        swing_type=swing_type,
    )


def make_structure(index, price, structure_type):
    swing_type = (
        SwingPointType.SWING_HIGH
        if structure_type in (
            MarketStructureType.HIGHER_HIGH,
            MarketStructureType.LOWER_HIGH,
        )
        else SwingPointType.SWING_LOW
    )

    return MarketStructurePoint(
        swing_point=make_swing(index, price, swing_type),
        structure_type=structure_type,
    )


def test_returns_empty_when_engine_disabled():
    engine = EqualHighEngine(
        config=EqualHighConfig(enabled=False)
    )

    assert engine.detect_equal_highs([]) == []


def test_detects_equal_high_from_two_highs():
    points = [
        make_structure(1, 110.00, MarketStructureType.HIGHER_HIGH),
        make_structure(3, 110.15, MarketStructureType.LOWER_HIGH),
    ]

    result = EqualHighEngine().detect_equal_highs(points)

    assert len(result) == 1
    assert result[0].swing_count() == 2
    assert result[0].is_valid()


def test_detects_single_cluster_from_three_equal_highs():
    points = [
        make_structure(1, 110.00, MarketStructureType.HIGHER_HIGH),
        make_structure(3, 110.10, MarketStructureType.LOWER_HIGH),
        make_structure(5, 110.18, MarketStructureType.HIGHER_HIGH),
    ]

    result = EqualHighEngine().detect_equal_highs(points)

    assert len(result) == 1
    assert result[0].swing_count() == 3


def test_ignores_lows():
    points = [
        make_structure(1, 90.0, MarketStructureType.HIGHER_LOW),
        make_structure(2, 85.0, MarketStructureType.LOWER_LOW),
    ]

    result = EqualHighEngine().detect_equal_highs(points)

    assert result == []


def test_respects_price_tolerance():
    points = [
        make_structure(1, 110.00, MarketStructureType.HIGHER_HIGH),
        make_structure(2, 111.00, MarketStructureType.LOWER_HIGH),
    ]

    result = EqualHighEngine().detect_equal_highs(points)

    assert result == []


def test_preserves_source_swings():
    points = [
        make_structure(1, 110.00, MarketStructureType.HIGHER_HIGH),
        make_structure(2, 110.15, MarketStructureType.LOWER_HIGH),
    ]

    result = EqualHighEngine().detect_equal_highs(points)

    assert result[0].source_swings[0] == points[0].swing_point
    assert result[0].source_swings[1] == points[1].swing_point
