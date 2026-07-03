from datetime import datetime, timedelta

from src.config.equal_level_config import EqualLevelConfig
from src.engines.equal_level_engine import EqualLevelEngine
from src.models.equal_high_point import EqualHighPoint
from src.models.equal_level_type import EqualLevelType
from src.models.equal_low_point import EqualLowPoint
from src.models.market_structure import MarketStructurePoint, MarketStructureType
from src.models.swing_point import SwingPoint, SwingPointType


def create_swing_point(
    index: int,
    price: float,
    swing_type: SwingPointType,
) -> SwingPoint:
    return SwingPoint(
        index=index,
        timestamp=datetime(2024, 1, 1) + timedelta(minutes=index),
        price=price,
        swing_type=swing_type,
    )


def create_structure_point(
    index: int,
    price: float,
    swing_type: SwingPointType,
    structure_type: MarketStructureType,
) -> MarketStructurePoint:
    return MarketStructurePoint(
        swing_point=create_swing_point(index, price, swing_type),
        structure_type=structure_type,
    )


def test_equal_level_engine_returns_empty_when_disabled():
    points = [
        create_structure_point(
            1,
            100.00,
            SwingPointType.SWING_HIGH,
            MarketStructureType.HIGHER_HIGH,
        ),
        create_structure_point(
            2,
            100.10,
            SwingPointType.SWING_HIGH,
            MarketStructureType.LOWER_HIGH,
        ),
    ]

    engine = EqualLevelEngine(config=EqualLevelConfig(enabled=False))

    result = engine.detect_equal_levels(points, EqualLevelType.HIGH)

    assert result == []


def test_equal_level_engine_detects_equal_highs():
    points = [
        create_structure_point(
            1,
            100.00,
            SwingPointType.SWING_HIGH,
            MarketStructureType.HIGHER_HIGH,
        ),
        create_structure_point(
            2,
            100.10,
            SwingPointType.SWING_HIGH,
            MarketStructureType.LOWER_HIGH,
        ),
    ]

    result = EqualLevelEngine().detect_equal_levels(points, EqualLevelType.HIGH)

    assert len(result) == 1
    assert isinstance(result[0], EqualHighPoint)
    assert result[0].index == 2
    assert result[0].price == 100.05
    assert result[0].swing_count() == 2
    assert result[0].is_valid() is True


def test_equal_level_engine_ignores_highs_outside_tolerance():
    points = [
        create_structure_point(
            1,
            100.00,
            SwingPointType.SWING_HIGH,
            MarketStructureType.HIGHER_HIGH,
        ),
        create_structure_point(
            2,
            101.00,
            SwingPointType.SWING_HIGH,
            MarketStructureType.LOWER_HIGH,
        ),
    ]

    result = EqualLevelEngine().detect_equal_levels(points, EqualLevelType.HIGH)

    assert result == []


def test_equal_level_engine_detects_equal_lows():
    points = [
        create_structure_point(
            1,
            90.00,
            SwingPointType.SWING_LOW,
            MarketStructureType.HIGHER_LOW,
        ),
        create_structure_point(
            2,
            90.10,
            SwingPointType.SWING_LOW,
            MarketStructureType.LOWER_LOW,
        ),
    ]

    result = EqualLevelEngine().detect_equal_levels(points, EqualLevelType.LOW)

    assert len(result) == 1
    assert isinstance(result[0], EqualLowPoint)
    assert result[0].index == 2
    assert result[0].price == 90.05
    assert result[0].swing_count() == 2
    assert result[0].is_valid() is True


def test_equal_level_engine_ignores_wrong_structure_type():
    points = [
        create_structure_point(
            1,
            100.00,
            SwingPointType.SWING_HIGH,
            MarketStructureType.HIGHER_HIGH,
        ),
        create_structure_point(
            2,
            100.10,
            SwingPointType.SWING_HIGH,
            MarketStructureType.LOWER_HIGH,
        ),
    ]

    result = EqualLevelEngine().detect_equal_levels(points, EqualLevelType.LOW)

    assert result == []