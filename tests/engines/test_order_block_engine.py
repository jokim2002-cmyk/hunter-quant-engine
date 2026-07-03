from datetime import datetime

from src.config.order_block_config import OrderBlockConfig
from src.engines.order_block_engine import OrderBlockEngine
from src.models.candle import Candle
from src.models.order_block_type import OrderBlockType


def create_candle(
    index: int,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    return Candle(
        datetime=datetime(2026, 1, 1, 9, index),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=1000,
    )


def test_detects_bullish_order_block():
    candles = [
        create_candle(0, 110.0, 112.0, 100.0, 102.0),
        create_candle(1, 102.0, 120.0, 101.0, 118.0),
    ]

    engine = OrderBlockEngine()
    order_blocks = engine.detect(candles)

    assert len(order_blocks) == 1
    assert order_blocks[0].candle_index == 0
    assert order_blocks[0].order_block_type == OrderBlockType.BULLISH
    assert order_blocks[0].high == 112.0
    assert order_blocks[0].low == 100.0


def test_detects_bearish_order_block():
    candles = [
        create_candle(0, 100.0, 112.0, 99.0, 110.0),
        create_candle(1, 110.0, 111.0, 90.0, 92.0),
    ]

    engine = OrderBlockEngine()
    order_blocks = engine.detect(candles)

    assert len(order_blocks) == 1
    assert order_blocks[0].candle_index == 0
    assert order_blocks[0].order_block_type == OrderBlockType.BEARISH
    assert order_blocks[0].high == 112.0
    assert order_blocks[0].low == 99.0


def test_returns_empty_when_disabled():
    candles = [
        create_candle(0, 110.0, 112.0, 100.0, 102.0),
        create_candle(1, 102.0, 120.0, 101.0, 118.0),
    ]

    config = OrderBlockConfig(enabled=False)
    engine = OrderBlockEngine(config=config)

    assert engine.detect(candles) == []


def test_returns_empty_when_not_enough_candles():
    candles = [
        create_candle(0, 110.0, 112.0, 100.0, 102.0),
    ]

    engine = OrderBlockEngine()

    assert engine.detect(candles) == []


def test_respects_minimum_displacement_size():
    candles = [
        create_candle(0, 110.0, 112.0, 100.0, 102.0),
        create_candle(1, 102.0, 103.0, 101.0, 102.5),
    ]

    config = OrderBlockConfig(minimum_displacement_size=5.0)
    engine = OrderBlockEngine(config=config)

    assert engine.detect(candles) == []


def test_requires_opposite_candle_by_default():
    candles = [
        create_candle(0, 100.0, 112.0, 99.0, 110.0),
        create_candle(1, 110.0, 120.0, 109.0, 118.0),
    ]

    engine = OrderBlockEngine()
    order_blocks = engine.detect(candles)

    assert order_blocks == []


def test_can_disable_opposite_candle_requirement():
    candles = [
        create_candle(0, 100.0, 112.0, 99.0, 110.0),
        create_candle(1, 110.0, 120.0, 109.0, 118.0),
    ]

    config = OrderBlockConfig(require_opposite_candle=False)
    engine = OrderBlockEngine(config=config)

    order_blocks = engine.detect(candles)

    assert len(order_blocks) == 1
    assert order_blocks[0].order_block_type == OrderBlockType.BULLISH