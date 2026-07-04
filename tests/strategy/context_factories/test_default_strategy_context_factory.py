"""
Default Strategy Context Factory Tests
"""

from datetime import datetime

from src.models.bos_point import BOSType
from src.models.candle import Candle
from src.models.choch_point import CHOCHType
from src.models.liquidity_sweep_type import LiquiditySweepType
from src.models.market_structure import MarketStructureType
from src.strategy.context_factories.default_strategy_context_factory import (
    DefaultStrategyContextFactory,
)


def _candle(
    candle_time: datetime,
    high: float,
    low: float,
    close: float,
) -> Candle:
    return Candle(
        datetime=candle_time,
        open=close,
        high=high,
        low=low,
        close=close,
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
    first_candle = _candle(
        datetime(2026, 1, 1, 9, 0),
        high=105.0,
        low=95.0,
        close=100.0,
    )
    second_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=106.0,
        low=96.0,
        close=101.0,
    )

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
        close=95.0,
    )
    second_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=101.0,
        low=91.0,
        close=96.0,
    )
    swing_high_candle = _candle(
        datetime(2026, 1, 1, 11, 0),
        high=110.0,
        low=99.0,
        close=105.0,
    )
    fourth_candle = _candle(
        datetime(2026, 1, 1, 12, 0),
        high=102.0,
        low=92.0,
        close=97.0,
    )
    fifth_candle = _candle(
        datetime(2026, 1, 1, 13, 0),
        high=103.0,
        low=93.0,
        close=98.0,
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


def test_create_populates_bos_events_from_market_structure_points():
    first_candle = _candle(
        datetime(2026, 1, 1, 9, 0),
        high=100.0,
        low=90.0,
        close=95.0,
    )
    second_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=101.0,
        low=91.0,
        close=96.0,
    )
    swing_high_candle = _candle(
        datetime(2026, 1, 1, 11, 0),
        high=110.0,
        low=99.0,
        close=105.0,
    )
    fourth_candle = _candle(
        datetime(2026, 1, 1, 12, 0),
        high=102.0,
        low=92.0,
        close=97.0,
    )
    fifth_candle = _candle(
        datetime(2026, 1, 1, 13, 0),
        high=103.0,
        low=93.0,
        close=98.0,
    )
    break_candle = _candle(
        datetime(2026, 1, 1, 14, 0),
        high=112.0,
        low=100.0,
        close=111.0,
    )

    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=break_candle.datetime,
        candles=(
            first_candle,
            second_candle,
            swing_high_candle,
            fourth_candle,
            fifth_candle,
            break_candle,
        ),
    )

    assert len(context.bos_events) == 1
    assert context.bos_events[0].bos_type is BOSType.BULLISH
    assert context.bos_events[0].break_price == 111.0
    assert context.bos_events[0].timestamp == break_candle.datetime


def test_create_populates_choch_events_from_market_structure_points():
    first_candle = _candle(
        datetime(2026, 1, 1, 9, 0),
        high=105.0,
        low=95.0,
        close=100.0,
    )
    second_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=104.0,
        low=94.0,
        close=99.0,
    )
    first_swing_low_candle = _candle(
        datetime(2026, 1, 1, 11, 0),
        high=103.0,
        low=80.0,
        close=95.0,
    )
    fourth_candle = _candle(
        datetime(2026, 1, 1, 12, 0),
        high=104.0,
        low=93.0,
        close=98.0,
    )
    fifth_candle = _candle(
        datetime(2026, 1, 1, 13, 0),
        high=105.0,
        low=92.0,
        close=99.0,
    )
    sixth_candle = _candle(
        datetime(2026, 1, 1, 14, 0),
        high=106.0,
        low=95.0,
        close=100.0,
    )
    higher_low_candle = _candle(
        datetime(2026, 1, 1, 15, 0),
        high=107.0,
        low=90.0,
        close=96.0,
    )
    eighth_candle = _candle(
        datetime(2026, 1, 1, 16, 0),
        high=108.0,
        low=91.0,
        close=97.0,
    )
    ninth_candle = _candle(
        datetime(2026, 1, 1, 17, 0),
        high=109.0,
        low=92.0,
        close=98.0,
    )
    break_candle = _candle(
        datetime(2026, 1, 1, 18, 0),
        high=100.0,
        low=88.0,
        close=89.0,
    )

    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=break_candle.datetime,
        candles=(
            first_candle,
            second_candle,
            first_swing_low_candle,
            fourth_candle,
            fifth_candle,
            sixth_candle,
            higher_low_candle,
            eighth_candle,
            ninth_candle,
            break_candle,
        ),
    )

    assert len(context.choch_events) == 1
    assert context.choch_events[0].choch_type is CHOCHType.BEARISH
    assert context.choch_events[0].break_price == 89.0
    assert context.choch_events[0].timestamp == break_candle.datetime


def test_create_populates_liquidity_points_from_market_structure_points():
    first_candle = _candle(
        datetime(2026, 1, 1, 9, 0),
        high=100.0,
        low=90.0,
        close=95.0,
    )
    second_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=101.0,
        low=91.0,
        close=96.0,
    )
    swing_high_candle = _candle(
        datetime(2026, 1, 1, 11, 0),
        high=110.0,
        low=99.0,
        close=105.0,
    )
    fourth_candle = _candle(
        datetime(2026, 1, 1, 12, 0),
        high=102.0,
        low=92.0,
        close=97.0,
    )
    fifth_candle = _candle(
        datetime(2026, 1, 1, 13, 0),
        high=103.0,
        low=93.0,
        close=98.0,
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

    assert len(context.liquidity_points) == 1
    assert context.liquidity_points[0].is_buy_side()
    assert context.liquidity_points[0].price == 110.0
    assert context.liquidity_points[0].timestamp == swing_high_candle.datetime


def test_create_populates_equal_high_points_from_market_structure_points():
    candles = (
        _candle(datetime(2026, 1, 1, 9, 0), high=100.0, low=90.0, close=95.0),
        _candle(datetime(2026, 1, 1, 10, 0), high=101.0, low=91.0, close=96.0),
        _candle(datetime(2026, 1, 1, 11, 0), high=110.0, low=99.0, close=105.0),
        _candle(datetime(2026, 1, 1, 12, 0), high=102.0, low=92.0, close=97.0),
        _candle(datetime(2026, 1, 1, 13, 0), high=100.0, low=90.0, close=95.0),
        _candle(datetime(2026, 1, 1, 14, 0), high=101.0, low=91.0, close=96.0),
        _candle(datetime(2026, 1, 1, 15, 0), high=110.1, low=99.0, close=105.0),
        _candle(datetime(2026, 1, 1, 16, 0), high=102.0, low=92.0, close=97.0),
        _candle(datetime(2026, 1, 1, 17, 0), high=101.0, low=91.0, close=96.0),
    )

    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=candles[-1].datetime,
        candles=candles,
    )

    assert len(context.equal_high_points) == 1
    assert context.equal_high_points[0].is_valid()
    assert context.equal_high_points[0].swing_count() == 2
    assert context.equal_high_points[0].price == 110.05


def test_create_populates_equal_low_points_from_market_structure_points():
    candles = (
        _candle(datetime(2026, 1, 1, 9, 0), high=105.0, low=95.0, close=100.0),
        _candle(datetime(2026, 1, 1, 10, 0), high=106.0, low=96.0, close=101.0),
        _candle(datetime(2026, 1, 1, 11, 0), high=100.0, low=90.0, close=95.0),
        _candle(datetime(2026, 1, 1, 12, 0), high=107.0, low=97.0, close=102.0),
        _candle(datetime(2026, 1, 1, 13, 0), high=108.0, low=98.0, close=103.0),
        _candle(datetime(2026, 1, 1, 14, 0), high=106.0, low=96.0, close=101.0),
        _candle(datetime(2026, 1, 1, 15, 0), high=100.0, low=90.1, close=95.0),
        _candle(datetime(2026, 1, 1, 16, 0), high=107.0, low=97.0, close=102.0),
        _candle(datetime(2026, 1, 1, 17, 0), high=108.0, low=98.0, close=103.0),
    )

    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=candles[-1].datetime,
        candles=candles,
    )

    assert len(context.equal_low_points) == 1
    assert context.equal_low_points[0].is_valid()
    assert context.equal_low_points[0].swing_count() == 2
    assert context.equal_low_points[0].price == 90.05


def test_create_populates_liquidity_clusters_from_liquidity_points():
    candles = (
        _candle(datetime(2026, 1, 1, 9, 0), high=100.0, low=90.0, close=95.0),
        _candle(datetime(2026, 1, 1, 10, 0), high=101.0, low=91.0, close=96.0),
        _candle(datetime(2026, 1, 1, 11, 0), high=110.0, low=99.0, close=105.0),
        _candle(datetime(2026, 1, 1, 12, 0), high=102.0, low=92.0, close=97.0),
        _candle(datetime(2026, 1, 1, 13, 0), high=100.0, low=90.0, close=95.0),
        _candle(datetime(2026, 1, 1, 14, 0), high=101.0, low=91.0, close=96.0),
        _candle(datetime(2026, 1, 1, 15, 0), high=110.1, low=99.0, close=105.0),
        _candle(datetime(2026, 1, 1, 16, 0), high=102.0, low=92.0, close=97.0),
        _candle(datetime(2026, 1, 1, 17, 0), high=101.0, low=91.0, close=96.0),
    )

    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=candles[-1].datetime,
        candles=candles,
    )

    assert len(context.liquidity_clusters) == 1
    assert context.liquidity_clusters[0].is_valid()
    assert context.liquidity_clusters[0].point_count() == 2
    assert context.liquidity_clusters[0].average_price == 110.05


def test_create_populates_liquidity_sweeps_from_liquidity_points():
    first_candle = _candle(
        datetime(2026, 1, 1, 9, 0),
        high=100.0,
        low=90.0,
        close=95.0,
    )
    second_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=101.0,
        low=91.0,
        close=96.0,
    )
    swing_high_candle = _candle(
        datetime(2026, 1, 1, 11, 0),
        high=110.0,
        low=99.0,
        close=105.0,
    )
    fourth_candle = _candle(
        datetime(2026, 1, 1, 12, 0),
        high=102.0,
        low=92.0,
        close=97.0,
    )
    fifth_candle = _candle(
        datetime(2026, 1, 1, 13, 0),
        high=103.0,
        low=93.0,
        close=98.0,
    )
    sweep_candle = _candle(
        datetime(2026, 1, 1, 14, 0),
        high=111.0,
        low=100.0,
        close=109.5,
    )

    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=sweep_candle.datetime,
        candles=(
            first_candle,
            second_candle,
            swing_high_candle,
            fourth_candle,
            fifth_candle,
            sweep_candle,
        ),
    )

    assert len(context.liquidity_sweeps) == 1
    assert context.liquidity_sweeps[0].sweep_type is LiquiditySweepType.HIGH
    assert context.liquidity_sweeps[0].sweep_price == 111.0
    assert context.liquidity_sweeps[0].liquidity_price == 110.0
    assert context.liquidity_sweeps[0].reclaimed is True


def test_create_populates_fair_value_gaps_from_candles():
    candles = (
        _candle(datetime(2026, 1, 1, 9, 0), high=101.0, low=99.0, close=100.0),
        _candle(datetime(2026, 1, 1, 10, 0), high=103.0, low=100.0, close=102.0),
        _candle(datetime(2026, 1, 1, 11, 0), high=105.0, low=103.0, close=104.0),
    )

    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=candles[-1].datetime,
        candles=candles,
    )

    assert len(context.fair_value_gaps) == 1
    assert context.fair_value_gaps[0].is_bullish()
    assert context.fair_value_gaps[0].low == 101.0
    assert context.fair_value_gaps[0].high == 103.0


def test_create_returns_empty_detection_events_when_no_swings_exist():
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


def test_create_leaves_unintegrated_detection_events_empty_for_now():
    context = DefaultStrategyContextFactory().create(
        symbol="TEST",
        timeframe="1H",
        analysis_time=datetime(2026, 1, 1, 9, 0),
        candles=(),
    )

    assert context.order_blocks == ()
