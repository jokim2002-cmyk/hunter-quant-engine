from datetime import datetime

from src.config.fair_value_gap_config import FairValueGapConfig
from src.engines.fair_value_gap_engine import FairValueGapEngine
from src.models.candle import Candle
from src.models.fair_value_gap_type import FairValueGapType


def make_candle(open_price, high, low, close):
    return Candle(
        datetime=datetime(2024, 1, 1),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def test_detect_bullish_fair_value_gap():
    candles = [
        make_candle(100, 101, 99, 100),
        make_candle(101, 103, 100, 102),
        make_candle(104, 105, 103, 104),
    ]

    engine = FairValueGapEngine()
    gaps = engine.detect(candles)

    assert len(gaps) == 1
    assert gaps[0].direction == FairValueGapType.BULLISH
    assert gaps[0].start_index == 0
    assert gaps[0].end_index == 2
    assert gaps[0].low == 101
    assert gaps[0].high == 103
    assert gaps[0].created_at == 2


def test_detect_bearish_fair_value_gap():
    candles = [
        make_candle(105, 106, 104, 105),
        make_candle(103, 104, 101, 102),
        make_candle(100, 101, 99, 100),
    ]

    engine = FairValueGapEngine()
    gaps = engine.detect(candles)

    assert len(gaps) == 1
    assert gaps[0].direction == FairValueGapType.BEARISH
    assert gaps[0].start_index == 0
    assert gaps[0].end_index == 2
    assert gaps[0].low == 101
    assert gaps[0].high == 104
    assert gaps[0].created_at == 2


def test_returns_empty_when_no_gap_exists():
    candles = [
        make_candle(100, 105, 99, 103),
        make_candle(103, 106, 102, 104),
        make_candle(104, 107, 101, 105),
    ]

    engine = FairValueGapEngine()
    gaps = engine.detect(candles)

    assert gaps == []


def test_returns_empty_when_disabled():
    candles = [
        make_candle(100, 101, 99, 100),
        make_candle(101, 103, 100, 102),
        make_candle(104, 105, 103, 104),
    ]

    config = FairValueGapConfig(enabled=False)
    engine = FairValueGapEngine(config=config)

    gaps = engine.detect(candles)

    assert gaps == []


def test_respects_minimum_gap_size():
    candles = [
        make_candle(100, 101, 99, 100),
        make_candle(101, 103, 100, 102),
        make_candle(104, 105, 103, 104),
    ]

    config = FairValueGapConfig(minimum_gap_size=3.0)
    engine = FairValueGapEngine(config=config)

    gaps = engine.detect(candles)

    assert gaps == []


def test_returns_empty_with_less_than_three_candles():
    candles = [
        make_candle(100, 101, 99, 100),
        make_candle(101, 103, 100, 102),
    ]

    engine = FairValueGapEngine()
    gaps = engine.detect(candles)

    assert gaps == []