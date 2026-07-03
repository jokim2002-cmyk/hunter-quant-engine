"""
Tests for PerformanceSummaryBuilder.
"""

from tests.builders.backtesting.performance_summary_builder import (
    PerformanceSummaryBuilder,
)


def test_performance_summary_builder_creates_default_performance_summary():
    summary = PerformanceSummaryBuilder().build()

    assert summary.total_trades == 0
    assert summary.winning_trades == 0
    assert summary.losing_trades == 0
    assert summary.win_rate == 0.0
    assert summary.total_pnl == 0.0
    assert summary.average_pnl == 0.0
    assert summary.max_drawdown == 0.0


def test_performance_summary_builder_allows_custom_values():
    summary = (
        PerformanceSummaryBuilder()
        .with_total_trades(10)
        .with_winning_trades(6)
        .with_losing_trades(4)
        .with_win_rate(0.6)
        .with_total_pnl(500.0)
        .with_average_pnl(50.0)
        .with_max_drawdown(100.0)
        .build()
    )

    assert summary.total_trades == 10
    assert summary.winning_trades == 6
    assert summary.losing_trades == 4
    assert summary.win_rate == 0.6
    assert summary.total_pnl == 500.0
    assert summary.average_pnl == 50.0
    assert summary.max_drawdown == 100.0
