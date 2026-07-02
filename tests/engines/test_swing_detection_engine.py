from datetime import datetime, timedelta

import pytest

from src.engines.swing_detection_engine import SwingDetectionEngine
from src.models.candle import Candle
from src.models.swing_point import SwingPointType


def make_candle(index, high, low):
    return Candle(
        datetime=datetime(2026, 1, 1, 9, 15) + timedelta(minutes=5 * index),
        open=100.0,
        high=high,
        low=low,
        close=100.0,
        volume=1000.0,
    )


def test_engine_returns_empty_list_for_no_candles():
    # Arrange
    engine = SwingDetectionEngine(lookback=1)
    candles = []

    # Act
    swing_points = engine.detect_swings(candles)

    # Assert
    assert swing_points == []


def test_engine_returns_empty_list_when_not_enough_candles():
    # Arrange
    engine = SwingDetectionEngine(lookback=2)
    candles = [
        make_candle(0, high=100, low=90),
        make_candle(1, high=105, low=95),
        make_candle(2, high=102, low=92),
    ]

    # Act
    swing_points = engine.detect_swings(candles)

    # Assert
    assert swing_points == []


def test_engine_rejects_invalid_lookback():
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        SwingDetectionEngine(lookback=0)


def test_engine_detects_single_swing_high():
    # Arrange
    engine = SwingDetectionEngine(lookback=1)
    candles = [
        make_candle(0, high=100, low=90),
        make_candle(1, high=110, low=95),
        make_candle(2, high=105, low=92),
    ]

    # Act
    swing_points = engine.detect_swings(candles)

    # Assert
    assert len(swing_points) == 1
    assert swing_points[0].index == 1
    assert swing_points[0].price == 110
    assert swing_points[0].swing_type == SwingPointType.SWING_HIGH


def test_engine_detects_single_swing_low():
    # Arrange
    engine = SwingDetectionEngine(lookback=1)
    candles = [
        make_candle(0, high=110, low=100),
        make_candle(1, high=105, low=90),
        make_candle(2, high=108, low=95),
    ]

    # Act
    swing_points = engine.detect_swings(candles)

    # Assert
    assert len(swing_points) == 1
    assert swing_points[0].index == 1
    assert swing_points[0].price == 90
    assert swing_points[0].swing_type == SwingPointType.SWING_LOW