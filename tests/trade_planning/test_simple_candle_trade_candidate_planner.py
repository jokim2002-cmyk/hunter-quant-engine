"""
Simple Candle Trade Candidate Planner Tests
"""

from datetime import datetime

from src.models.candle import Candle
from src.strategy.signal_type import SignalType
from src.trade_planning.simple_candle_trade_candidate_planner import (
    SimpleCandleTradeCandidatePlanner,
)
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder
from tests.builders.strategy.trade_signal_builder import TradeSignalBuilder


def _candle(
    close: float = 100.0,
    high: float = 105.0,
    low: float = 95.0,
) -> Candle:
    return Candle(
        datetime=datetime(2026, 1, 1, 10, 0),
        open=100.0,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
    )


def test_plan_creates_long_candidate_from_latest_candle():
    signal = TradeSignalBuilder().long().build()
    candle = _candle(close=101.0, high=106.0, low=96.0)
    context = StrategyContextBuilder().with_candles(candle).build()

    candidates = SimpleCandleTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].signal is signal
    assert candidates[0].entry_price == 101.0
    assert candidates[0].stop_loss == 96.0


def test_plan_creates_short_candidate_from_latest_candle():
    signal = TradeSignalBuilder().short().build()
    candle = _candle(close=99.0, high=104.0, low=94.0)
    context = StrategyContextBuilder().with_candles(candle).build()

    candidates = SimpleCandleTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].signal is signal
    assert candidates[0].entry_price == 99.0
    assert candidates[0].stop_loss == 104.0


def test_plan_uses_latest_candle_when_multiple_candles_exist():
    signal = TradeSignalBuilder().long().build()
    old_candle = _candle(close=100.0, high=105.0, low=95.0)
    latest_candle = _candle(close=110.0, high=115.0, low=108.0)
    context = (
        StrategyContextBuilder()
        .with_candles(old_candle, latest_candle)
        .build()
    )

    candidates = SimpleCandleTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates[0].entry_price == 110.0
    assert candidates[0].stop_loss == 108.0


def test_plan_returns_empty_tuple_for_neutral_signal():
    signal = TradeSignalBuilder().neutral().build()
    context = StrategyContextBuilder().with_candles(_candle()).build()

    candidates = SimpleCandleTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates == ()


def test_plan_returns_empty_tuple_when_context_has_no_candles():
    signal = TradeSignalBuilder().long().build()
    context = StrategyContextBuilder().build()

    candidates = SimpleCandleTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates == ()


def test_plan_preserves_signal_type():
    signal = TradeSignalBuilder().short().build()
    context = StrategyContextBuilder().with_candles(_candle()).build()

    candidates = SimpleCandleTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates[0].signal.signal_type is SignalType.SHORT
