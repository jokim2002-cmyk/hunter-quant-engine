from datetime import datetime, timedelta

from src.engines.choch_engine import CHOCHEngine
from src.models.candle import Candle
from src.models.choch_point import CHOCHType
from src.models.market_structure import MarketStructurePoint, MarketStructureType
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


def make_swing_point(index, price, swing_type):
    return SwingPoint(
        index=index,
        timestamp=datetime(2026, 1, 1, 9, 15) + timedelta(minutes=5 * index),
        price=price,
        swing_type=swing_type,
    )


def make_market_structure_point(index, price, swing_type, structure_type):
    swing_point = make_swing_point(
        index=index,
        price=price,
        swing_type=swing_type,
    )

    return MarketStructurePoint(
        swing_point=swing_point,
        structure_type=structure_type,
    )


def test_choch_engine_returns_empty_list_when_no_candles():
    engine = CHOCHEngine()

    result = engine.detect_choch([], [])

    assert result == []


def test_choch_engine_returns_empty_when_no_market_structure_points():
    candles = [
        make_candle(0, 100),
        make_candle(1, 101),
    ]

    engine = CHOCHEngine()

    result = engine.detect_choch(candles, [])

    assert result == []


def test_choch_engine_detects_bearish_choch_when_higher_low_breaks():
    candles = [
        make_candle(0, 100),
        make_candle(1, 95),
        make_candle(2, 89),
    ]

    higher_low = make_market_structure_point(
        index=1,
        price=90,
        swing_type=SwingPointType.SWING_LOW,
        structure_type=MarketStructureType.HIGHER_LOW,
    )

    engine = CHOCHEngine()

    result = engine.detect_choch(candles, [higher_low])

    assert len(result) == 1
    assert result[0].index == 2
    assert result[0].break_price == 89
    assert result[0].choch_type == CHOCHType.BEARISH
    assert result[0].broken_swing == higher_low.swing_point


def test_choch_engine_detects_bullish_choch_when_lower_high_breaks():
    candles = [
        make_candle(0, 100),
        make_candle(1, 105),
        make_candle(2, 111),
    ]

    lower_high = make_market_structure_point(
        index=1,
        price=110,
        swing_type=SwingPointType.SWING_HIGH,
        structure_type=MarketStructureType.LOWER_HIGH,
    )

    engine = CHOCHEngine()

    result = engine.detect_choch(candles, [lower_high])

    assert len(result) == 1
    assert result[0].index == 2
    assert result[0].break_price == 111
    assert result[0].choch_type == CHOCHType.BULLISH
    assert result[0].broken_swing == lower_high.swing_point


def test_choch_engine_ignores_higher_high():
    candles = [
        make_candle(0, 100),
        make_candle(1, 105),
        make_candle(2, 111),
    ]

    higher_high = make_market_structure_point(
        index=1,
        price=110,
        swing_type=SwingPointType.SWING_HIGH,
        structure_type=MarketStructureType.HIGHER_HIGH,
    )

    engine = CHOCHEngine()

    result = engine.detect_choch(candles, [higher_high])

    assert result == []


def test_choch_engine_ignores_lower_low():
    candles = [
        make_candle(0, 100),
        make_candle(1, 95),
        make_candle(2, 89),
    ]

    lower_low = make_market_structure_point(
        index=1,
        price=90,
        swing_type=SwingPointType.SWING_LOW,
        structure_type=MarketStructureType.LOWER_LOW,
    )

    engine = CHOCHEngine()

    result = engine.detect_choch(candles, [lower_low])

    assert result == []


def test_choch_engine_does_not_detect_when_only_wick_breaks():
    candles = [
        make_candle(0, 100),
        Candle(
            datetime=datetime(2026, 1, 1, 9, 20),
            open=109,
            high=111,
            low=108,
            close=109,
            volume=1000,
        ),
    ]

    lower_high = make_market_structure_point(
        index=0,
        price=110,
        swing_type=SwingPointType.SWING_HIGH,
        structure_type=MarketStructureType.LOWER_HIGH,
    )

    engine = CHOCHEngine()

    result = engine.detect_choch(candles, [lower_high])

    assert result == []
