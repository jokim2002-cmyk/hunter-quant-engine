"""
Default Strategy Context Factory Tests
"""

from datetime import datetime

from src.models.candle import Candle
from src.models.market_structure import MarketStructureType
from src.strategy.context_factories.default_strategy_context_factory import (
    DefaultStrategyContextFactory,
)


def _candle(
    candle_time: datetime = datetime(2026, 1, 1, 9, 0),
    high: float = 105.0,
    low: float = 95.0,
) -> Candle:
    return Candle(
        datetime=candle_time,
        open=100.0,
        high=high,
        low=low,
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


def test_create_populates_market_structure_points_from_detected_swings():
    first_candle = _candle(
        datetime(2026, 1, 1, 9, 0),
        high=100.0,
        low=90.0,
    )
    second_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=101.0,
        low=91.0,
    )
    swing_high_candle = _candle(
        datetime(2026, 1, 1, 11, 0),
        high=110.0,
        low=99.0,
    )
    fourth_candle = _candle(
        datetime(2026, 1, 1, 12, 0),
        high=102.0,
        low=92.0,
    )
    fifth_candle = _candle(
        datetime(2026, 1, 1, 13, 0),
        high=103.0,
        low=93.0,
    )

    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=fifth_candle.datetime,
        candles=(
            first_candle,
            second_candle,
            swing_high_candle,
            fourth_candle,
            fifth_candle,
        ),
    )

    assert len(context.market_structure_points) == 1
    assert (
        context.market_structure_points[0].structure_type
        is MarketStructureType.HIGHER_HIGH
    )
    assert context.market_structure_points[0].swing_point.price == 110.0
    assert (
        context.market_structure_points[0].swing_point.timestamp
        == swing_high_candle.datetime
    )


def test_create_returns_empty_market_structure_when_no_swings_exist():
    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=datetime(2026, 1, 1, 9, 0),
        candles=(),
    )

    assert context.market_structure_points == ()


def test_create_leaves_other_detection_events_empty_for_now():
    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=datetime(2026, 1, 1, 9, 0),
        candles=(),
    )

    assert context.bos_events == ()
    assert context.choch_events == ()
    assert context.liquidity_points == ()
    assert context.equal_high_points == ()
    assert context.equal_low_points == ()
    assert context.liquidity_clusters == ()
    assert context.liquidity_sweeps == ()
    assert context.fair_value_gaps == ()
    assert context.order_blocks == ()
