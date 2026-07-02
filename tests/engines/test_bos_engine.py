from datetime import datetime, timedelta

from src.engines.bos_engine import BOSEngine
from src.models.candle import Candle
from src.models.bos_point import BOSType
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


def test_bos_engine_returns_empty_list_when_no_candles():
    engine = BOSEngine()

    result = engine.detect_bos([], [])

    assert result == []


def test_bos_engine_detects_bullish_bos_on_close_above_swing_high():
    candles = [
        make_candle(0, 100),
        make_candle(1, 105),
        make_candle(2, 111),
    ]

    swing_high = SwingPoint(
        index=1,
        timestamp=candles[1].datetime,
        price=110.0,
        swing_type=SwingPointType.SWING_HIGH,
    )

    engine = BOSEngine()

    result = engine.detect_bos(candles, [swing_high])

    assert len(result) == 1
    assert result[0].index == 2
    assert result[0].break_price == 111
    assert result[0].bos_type == BOSType.BULLISH
    assert result[0].broken_swing == swing_high


def test_bos_engine_detects_bearish_bos_on_close_below_swing_low():
    candles = [
        make_candle(0, 100),
        make_candle(1, 95),
        make_candle(2, 89),
    ]

    swing_low = SwingPoint(
        index=1,
        timestamp=candles[1].datetime,
        price=90.0,
        swing_type=SwingPointType.SWING_LOW,
    )

    engine = BOSEngine()

    result = engine.detect_bos(candles, [swing_low])

    assert len(result) == 1
    assert result[0].index == 2
    assert result[0].break_price == 89
    assert result[0].bos_type == BOSType.BEARISH
    assert result[0].broken_swing == swing_low
