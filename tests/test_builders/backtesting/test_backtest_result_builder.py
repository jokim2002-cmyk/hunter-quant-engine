"""
Tests for BacktestResultBuilder.
"""

from tests.builders.backtesting.backtest_result_builder import BacktestResultBuilder
from tests.builders.backtesting.performance_summary_builder import (
    PerformanceSummaryBuilder,
)
from tests.builders.backtesting.trade_result_builder import TradeResultBuilder


def test_backtest_result_builder_creates_default_backtest_result():
    result = BacktestResultBuilder().build()

    assert result.trades == ()
    assert result.performance_summary.total_trades == 0


def test_backtest_result_builder_allows_custom_values():
    trade = TradeResultBuilder().build()
    summary = (
        PerformanceSummaryBuilder()
        .with_total_trades(1)
        .with_winning_trades(1)
        .with_losing_trades(0)
        .with_win_rate(1.0)
        .with_total_pnl(200.0)
        .with_average_pnl(200.0)
        .with_max_drawdown(0.0)
        .build()
    )

    result = (
        BacktestResultBuilder()
        .with_trades(trade)
        .with_performance_summary(summary)
        .build()
    )

    assert result.trades == (trade,)
    assert result.performance_summary == summary
