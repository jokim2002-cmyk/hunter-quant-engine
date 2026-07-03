from datetime import datetime

from src.config.liquidity_sweep_config import LiquiditySweepConfig
from src.engines.liquidity_sweep_engine import LiquiditySweepEngine
from src.models.candle import Candle
from src.models.liquidity_point import LiquidityPoint, LiquidityType
from src.models.liquidity_sweep_type import LiquiditySweepType


def make_candle(open_price, high, low, close):
    return Candle(
        datetime=datetime(2024, 1, 1),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100,
    )


def make_liquidity_point(index, price, liquidity_type):
    return LiquidityPoint(
        index=index,
        timestamp=datetime(2024, 1, 1),
        price=price,
        liquidity_type=liquidity_type,
        source_swing=None,
    )


def test_detect_buy_side_liquidity_sweep():
    candles = [
        make_candle(99, 100, 98, 99),
        make_candle(100, 100.50, 99, 99.80),
    ]

    liquidity_points = [
        make_liquidity_point(
            index=0,
            price=100.00,
            liquidity_type=LiquidityType.BUY_SIDE,
        )
    ]

    engine = LiquiditySweepEngine()
    sweeps = engine.detect(candles, liquidity_points)

    assert len(sweeps) == 1
    assert sweeps[0].candle_index == 1
    assert sweeps[0].liquidity_index == 0
    assert sweeps[0].sweep_price == 100.50
    assert sweeps[0].liquidity_price == 100.00
    assert sweeps[0].break_distance == 0.50
    assert sweeps[0].reclaimed is True
    assert sweeps[0].sweep_type == LiquiditySweepType.HIGH
    assert sweeps[0].created_at == 1


def test_detect_sell_side_liquidity_sweep():
    candles = [
        make_candle(101, 102, 100, 101),
        make_candle(100, 101, 99.50, 100.20),
    ]

    liquidity_points = [
        make_liquidity_point(
            index=0,
            price=100.00,
            liquidity_type=LiquidityType.SELL_SIDE,
        )
    ]

    engine = LiquiditySweepEngine()
    sweeps = engine.detect(candles, liquidity_points)

    assert len(sweeps) == 1
    assert sweeps[0].candle_index == 1
    assert sweeps[0].liquidity_index == 0
    assert sweeps[0].sweep_price == 99.50
    assert sweeps[0].liquidity_price == 100.00
    assert sweeps[0].break_distance == 0.50
    assert sweeps[0].reclaimed is True
    assert sweeps[0].sweep_type == LiquiditySweepType.LOW
    assert sweeps[0].created_at == 1


def test_returns_empty_when_disabled():
    candles = [
        make_candle(99, 100, 98, 99),
        make_candle(100, 100.50, 99, 99.80),
    ]

    liquidity_points = [
        make_liquidity_point(0, 100.00, LiquidityType.BUY_SIDE)
    ]

    config = LiquiditySweepConfig(enabled=False)
    engine = LiquiditySweepEngine(config=config)

    sweeps = engine.detect(candles, liquidity_points)

    assert sweeps == []


def test_requires_close_back_inside_by_default():
    candles = [
        make_candle(99, 100, 98, 99),
        make_candle(100, 100.50, 99, 100.20),
    ]

    liquidity_points = [
        make_liquidity_point(0, 100.00, LiquidityType.BUY_SIDE)
    ]

    engine = LiquiditySweepEngine()
    sweeps = engine.detect(candles, liquidity_points)

    assert sweeps == []


def test_can_detect_without_close_back_inside_when_config_allows():
    candles = [
        make_candle(99, 100, 98, 99),
        make_candle(100, 100.50, 99, 100.20),
    ]

    liquidity_points = [
        make_liquidity_point(0, 100.00, LiquidityType.BUY_SIDE)
    ]

    config = LiquiditySweepConfig(require_close_back_inside=False)
    engine = LiquiditySweepEngine(config=config)

    sweeps = engine.detect(candles, liquidity_points)

    assert len(sweeps) == 1
    assert sweeps[0].reclaimed is False
    assert sweeps[0].sweep_type == LiquiditySweepType.HIGH


def test_respects_sweep_tolerance():
    candles = [
        make_candle(99, 100, 98, 99),
        make_candle(100, 100.20, 99, 99.80),
    ]

    liquidity_points = [
        make_liquidity_point(0, 100.00, LiquidityType.BUY_SIDE)
    ]

    config = LiquiditySweepConfig(sweep_tolerance=0.50)
    engine = LiquiditySweepEngine(config=config)

    sweeps = engine.detect(candles, liquidity_points)

    assert sweeps == []


def test_returns_empty_when_no_liquidity_points():
    candles = [
        make_candle(99, 100, 98, 99),
        make_candle(100, 100.50, 99, 99.80),
    ]

    engine = LiquiditySweepEngine()
    sweeps = engine.detect(candles, [])

    assert sweeps == []