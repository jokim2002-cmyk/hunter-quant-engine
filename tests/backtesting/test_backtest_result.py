"""
Tests for BacktestResult.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from src.backtesting.backtest_result import BacktestResult
from src.backtesting.performance_summary import PerformanceSummary
from src.backtesting.trade_result import TradeResult
from src.strategy.signal_type import SignalType


def test_backtest_result_can_be_created():
    trade = TradeResult(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        exit_price=110.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size=20.0,
        pnl=200.0,
        risk_multiple=2.0,
        opened_at=datetime(2026, 1, 1),
        closed_at=datetime(2026, 1, 2),
    )
    summary = PerformanceSummary(
        total_trades=1,
        winning_trades=1,
        losing_trades=0,
        win_rate=1.0,
        total_pnl=200.0,
        average_pnl=200.0,
        max_drawdown=0.0,
    )

    result = BacktestResult(
        trades=(trade,),
        performance_summary=summary,
    )

    assert result.trades == (trade,)
    assert result.performance_summary == summary


def test_backtest_result_can_be_empty():
    summary = PerformanceSummary(
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate=0.0,
        total_pnl=0.0,
        average_pnl=0.0,
        max_drawdown=0.0,
    )

    result = BacktestResult(
        trades=(),
        performance_summary=summary,
    )

    assert result.trades == ()
    assert result.performance_summary == summary


def test_backtest_result_is_immutable():
    summary = PerformanceSummary(
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate=0.0,
        total_pnl=0.0,
        average_pnl=0.0,
        max_drawdown=0.0,
    )
    result = BacktestResult(
        trades=(),
        performance_summary=summary,
    )

    with pytest.raises(FrozenInstanceError):
        result.trades = ()


def test_raises_error_when_summary_trade_count_does_not_match_trades():
    trade = TradeResult(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        exit_price=110.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size=20.0,
        pnl=200.0,
        risk_multiple=2.0,
        opened_at=datetime(2026, 1, 1),
        closed_at=datetime(2026, 1, 2),
    )
    summary = PerformanceSummary(
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate=0.0,
        total_pnl=0.0,
        average_pnl=0.0,
        max_drawdown=0.0,
    )

    with pytest.raises(
        ValueError,
        match="performance_summary.total_trades must match number of trades.",
    ):
        BacktestResult(
            trades=(trade,),
            performance_summary=summary,
        )
