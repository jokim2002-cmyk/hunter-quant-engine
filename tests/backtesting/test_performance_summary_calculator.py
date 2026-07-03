"""
Tests for PerformanceSummaryCalculator.
"""

import pytest

from src.backtesting.performance_summary_calculator import (
    PerformanceSummaryCalculator,
)
from tests.builders.backtesting.trade_result_builder import TradeResultBuilder


def test_calculates_empty_performance_summary_when_there_are_no_trades():
    summary = PerformanceSummaryCalculator().calculate(())

    assert summary.total_trades == 0
    assert summary.winning_trades == 0
    assert summary.losing_trades == 0
    assert summary.win_rate == 0.0
    assert summary.total_pnl == 0.0
    assert summary.average_pnl == 0.0
    assert summary.max_drawdown == 0.0


def test_calculates_performance_summary_for_single_winning_trade():
    trade = TradeResultBuilder().with_pnl(200.0).build()

    summary = PerformanceSummaryCalculator().calculate((trade,))

    assert summary.total_trades == 1
    assert summary.winning_trades == 1
    assert summary.losing_trades == 0
    assert summary.win_rate == 1.0
    assert summary.total_pnl == 200.0
    assert summary.average_pnl == 200.0
    assert summary.max_drawdown == 0.0


def test_calculates_performance_summary_for_winning_and_losing_trades():
    winning_trade = TradeResultBuilder().with_pnl(300.0).build()
    losing_trade = TradeResultBuilder().with_pnl(-100.0).build()

    summary = PerformanceSummaryCalculator().calculate(
        (winning_trade, losing_trade)
    )

    assert summary.total_trades == 2
    assert summary.winning_trades == 1
    assert summary.losing_trades == 1
    assert summary.win_rate == 0.5
    assert summary.total_pnl == 200.0
    assert summary.average_pnl == 100.0
    assert summary.max_drawdown == 100.0


def test_break_even_trades_are_not_counted_as_wins_or_losses():
    winning_trade = TradeResultBuilder().with_pnl(100.0).build()
    losing_trade = TradeResultBuilder().with_pnl(-50.0).build()
    break_even_trade = TradeResultBuilder().with_pnl(0.0).build()

    summary = PerformanceSummaryCalculator().calculate(
        (winning_trade, losing_trade, break_even_trade)
    )

    assert summary.total_trades == 3
    assert summary.winning_trades == 1
    assert summary.losing_trades == 1
    assert summary.win_rate == pytest.approx(1 / 3)


def test_calculates_max_drawdown_from_ordered_trade_results():
    first_trade = TradeResultBuilder().with_pnl(100.0).build()
    second_trade = TradeResultBuilder().with_pnl(-40.0).build()
    third_trade = TradeResultBuilder().with_pnl(20.0).build()
    fourth_trade = TradeResultBuilder().with_pnl(-90.0).build()

    summary = PerformanceSummaryCalculator().calculate(
        (first_trade, second_trade, third_trade, fourth_trade)
    )

    assert summary.max_drawdown == 110.0
