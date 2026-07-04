"""
Default Strategy Context Factory Tests
"""

from datetime import datetime

from src.models.candle import Candle
from src.strategy.context_factories.default_strategy_context_factory import (
    DefaultStrategyContextFactory,
)


def _candle(
    candle_time: datetime = datetime(2026, 1, 1, 9, 0),
) -> Candle:
    return Candle(
        datetime=candle_time,
        open=100.0,
        high=105.0,
        low=95.0,
        close=100.0,
        volume=1000.0,
    )


def test_create_sets_context_metadata():
    analysis_time = datetime(2026, 1, 1, 9, 0)

    context = DefaultStrategyContextFactory().create(
        symbol="EURUSD",
        timeframe="1H",
        analysis_time=analysis_time,
        candles=(),
    )

    assert context.symbol == "EURUSD"
    assert context.timeframe == "1H"
    assert context.analysis_time == analysis_time


def test_create_sets_context_candles():
    first_candle = _candle(datetime(2026, 1, 1, 9, 0))
    second_candle = _candle(datetime(2026, 1, 1, 10, 0))

    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=second_candle.datetime,
        candles=(first_candle, second_candle),
    )

    assert context.candles == (first_candle, second_candle)


def test_create_leaves_detection_events_empty_in_v1():
    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=datetime(2026, 1, 1, 9, 0),
        candles=(),
    )

    assert context.market_structure_points == ()
    assert context.bos_events == ()
    assert context.choch_events == ()
    assert context.liquidity_points == ()
    assert context.equal_high_points == ()
    assert context.equal_low_points == ()
    assert context.liquidity_clusters == ()
    assert context.liquidity_sweeps == ()
    assert context.fair_value_gaps == ()
    assert context.order_blocks == ()
