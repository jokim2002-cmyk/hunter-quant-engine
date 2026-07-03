"""
Tests for OHLCTradeExecutionSimulator.
"""

from datetime import datetime

import pytest

from src.backtesting.ohlc_trade_execution_simulator import (
    OHLCTradeExecutionSimulator,
)
from src.backtesting.price_fill_result import PriceFillResult
from src.models.candle import Candle
from src.risk.trade_plan import TradePlan
from src.strategy.signal_type import SignalType


def _candle(
    candle_time: datetime,
    high: float,
    low: float,
) -> Candle:
    return Candle(
        datetime=candle_time,
        open=100.0,
        high=high,
        low=low,
        close=100.0,
        volume=1000.0,
    )


def _long_trade_plan() -> TradePlan:
    return TradePlan(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size=10.0,
        risk_amount=50.0,
        reward_amount=100.0,
        created_at=datetime(2026, 1, 1, 9, 0),
    )


def _short_trade_plan() -> TradePlan:
    return TradePlan(
        signal_type=SignalType.SHORT,
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
        position_size=10.0,
        risk_amount=50.0,
        reward_amount=100.0,
        created_at=datetime(2026, 1, 1, 9, 0),
    )


def test_returns_none_when_no_candles_are_available():
    result = OHLCTradeExecutionSimulator().simulate(
        trade_plan=_long_trade_plan(),
        candles=(),
    )

    assert result is None


def test_returns_none_when_trade_never_closes():
    candles = (
        _candle(datetime(2026, 1, 1, 10, 0), high=108.0, low=96.0),
        _candle(datetime(2026, 1, 1, 11, 0), high=109.0, low=97.0),
    )

    result = OHLCTradeExecutionSimulator().simulate(
        trade_plan=_long_trade_plan(),
        candles=candles,
    )

    assert result is None


def test_creates_trade_result_when_long_trade_hits_take_profit():
    trade_plan = _long_trade_plan()
    closing_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=110.0,
        low=96.0,
    )

    result = OHLCTradeExecutionSimulator().simulate(
        trade_plan=trade_plan,
        candles=(closing_candle,),
    )

    assert result is not None
    assert result.signal_type is SignalType.LONG
    assert result.entry_price == 100.0
    assert result.exit_price == 110.0
    assert result.stop_loss == 95.0
    assert result.take_profit == 110.0
    assert result.position_size == 10.0
    assert result.pnl == 100.0
    assert result.risk_multiple == 2.0
    assert result.opened_at == trade_plan.created_at
    assert result.closed_at == closing_candle.datetime


def test_creates_trade_result_when_long_trade_hits_stop_loss():
    result = OHLCTradeExecutionSimulator().simulate(
        trade_plan=_long_trade_plan(),
        candles=(
            _candle(datetime(2026, 1, 1, 10, 0), high=108.0, low=95.0),
        ),
    )

    assert result is not None
    assert result.exit_price == 95.0
    assert result.pnl == -50.0
    assert result.risk_multiple == -1.0


def test_creates_trade_result_when_short_trade_hits_take_profit():
    result = OHLCTradeExecutionSimulator().simulate(
        trade_plan=_short_trade_plan(),
        candles=(
            _candle(datetime(2026, 1, 1, 10, 0), high=104.0, low=90.0),
        ),
    )

    assert result is not None
    assert result.signal_type is SignalType.SHORT
    assert result.exit_price == 90.0
    assert result.pnl == 100.0
    assert result.risk_multiple == 2.0


def test_creates_trade_result_when_short_trade_hits_stop_loss():
    result = OHLCTradeExecutionSimulator().simulate(
        trade_plan=_short_trade_plan(),
        candles=(
            _candle(datetime(2026, 1, 1, 10, 0), high=105.0, low=92.0),
        ),
    )

    assert result is not None
    assert result.exit_price == 105.0
    assert result.pnl == -50.0
    assert result.risk_multiple == -1.0


def test_closes_trade_on_first_filled_candle():
    trade_plan = _long_trade_plan()
    first_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=108.0,
        low=96.0,
    )
    second_candle = _candle(
        datetime(2026, 1, 1, 11, 0),
        high=110.0,
        low=96.0,
    )
    third_candle = _candle(
        datetime(2026, 1, 1, 12, 0),
        high=120.0,
        low=90.0,
    )

    result = OHLCTradeExecutionSimulator().simulate(
        trade_plan=trade_plan,
        candles=(first_candle, second_candle, third_candle),
    )

    assert result is not None
    assert result.exit_price == 110.0
    assert result.closed_at == second_candle.datetime


class BrokenPriceFillModel:
    def evaluate(self, trade_plan, candle):
        return PriceFillResult(
            filled=True,
            fill_price=None,
            reason="broken",
        )


def test_raises_error_when_fill_result_is_filled_without_fill_price():
    simulator = OHLCTradeExecutionSimulator(
        price_fill_model=BrokenPriceFillModel(),
    )

    with pytest.raises(
        ValueError,
        match="Filled price result must include fill_price.",
    ):
        simulator.simulate(
            trade_plan=_long_trade_plan(),
            candles=(
                _candle(datetime(2026, 1, 1, 10, 0), high=110.0, low=96.0),
            ),
        )
