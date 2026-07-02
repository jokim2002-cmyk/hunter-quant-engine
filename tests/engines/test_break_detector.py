from datetime import datetime, timedelta

from src.engines.helpers.break_detector import BreakDetector
from src.models.candle import Candle
from src.models.swing_point import SwingPoint, SwingPointType


def make_candle(index, close):
    return Candle(
        datetime=datetime(2026, 1, 1, 9, 15) + timedelta(minutes=5 * index),
        open=100.0,
        high=close,
        low=close,
        close=close,
        volume=1000.0,
    )


def test_break_detector_finds_bullish_close_break():
    candles = [
        make_candle(0, 100),
        make_candle(1, 105),
        make_candle(2, 111),
    ]

    swing_high = SwingPoint(
        index=1,
        timestamp=candles[1].datetime,
        price=110,
        swing_type=SwingPointType.SWING_HIGH,
    )

    detector = BreakDetector()

    result = detector.find_close_break(candles, swing_high)

    assert result is not None

    break_index, break_candle = result

    assert break_index == 2
    assert break_candle.close == 111


def test_break_detector_finds_bearish_close_break():
    candles = [
        make_candle(0, 100),
        make_candle(1, 95),
        make_candle(2, 89),
    ]

    swing_low = SwingPoint(
        index=1,
        timestamp=candles[1].datetime,
        price=90,
        swing_type=SwingPointType.SWING_LOW,
    )

    detector = BreakDetector()

    result = detector.find_close_break(candles, swing_low)

    assert result is not None

    break_index, break_candle = result

    assert break_index == 2
    assert break_candle.close == 89


def test_break_detector_returns_none_when_no_close_break():
    candles = [
        make_candle(0, 100),
        make_candle(1, 105),
        make_candle(2, 109),
    ]

    swing_high = SwingPoint(
        index=1,
        timestamp=candles[1].datetime,
        price=110,
        swing_type=SwingPointType.SWING_HIGH,
    )

    detector = BreakDetector()

    result = detector.find_close_break(candles, swing_high)

    assert result is None
