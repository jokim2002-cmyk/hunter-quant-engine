"""
Tests for PerformanceSummary.
"""

from dataclasses import FrozenInstanceError

import pytest

from src.backtesting.performance_summary import PerformanceSummary


def test_performance_summary_can_be_created():
    summary = PerformanceSummary(
        total_trades=10,
        winning_trades=6,
        losing_trades=4,
        win_rate=0.6,
        total_pnl=500.0,
        average_pnl=50.0,
        max_drawdown=100.0,
    )

    assert summary.total_trades == 10
    assert summary.winning_trades == 6
    assert summary.losing_trades == 4
    assert summary.win_rate == 0.6
    assert summary.total_pnl == 500.0
    assert summary.average_pnl == 50.0
    assert summary.max_drawdown == 100.0


def test_performance_summary_is_immutable():
    summary = PerformanceSummary(
        total_trades=10,
        winning_trades=6,
        losing_trades=4,
        win_rate=0.6,
        total_pnl=500.0,
        average_pnl=50.0,
        max_drawdown=100.0,
    )

    with pytest.raises(FrozenInstanceError):
        summary.total_pnl = 600.0


def test_allows_empty_performance_summary():
    summary = PerformanceSummary(
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate=0.0,
        total_pnl=0.0,
        average_pnl=0.0,
        max_drawdown=0.0,
    )

    assert summary.total_trades == 0
    assert summary.winning_trades == 0
    assert summary.losing_trades == 0
    assert summary.win_rate == 0.0
    assert summary.total_pnl == 0.0
    assert summary.average_pnl == 0.0
    assert summary.max_drawdown == 0.0


def test_raises_error_when_total_trades_is_negative():
    with pytest.raises(ValueError, match="total_trades cannot be negative."):
        PerformanceSummary(
            total_trades=-1,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            average_pnl=0.0,
            max_drawdown=0.0,
        )


def test_raises_error_when_winning_trades_is_negative():
    with pytest.raises(ValueError, match="winning_trades cannot be negative."):
        PerformanceSummary(
            total_trades=10,
            winning_trades=-1,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            average_pnl=0.0,
            max_drawdown=0.0,
        )


def test_raises_error_when_losing_trades_is_negative():
    with pytest.raises(ValueError, match="losing_trades cannot be negative."):
        PerformanceSummary(
            total_trades=10,
            winning_trades=0,
            losing_trades=-1,
            win_rate=0.0,
            total_pnl=0.0,
            average_pnl=0.0,
            max_drawdown=0.0,
        )


def test_raises_error_when_win_and_loss_count_exceeds_total_trades():
    with pytest.raises(
        ValueError,
        match="winning_trades and losing_trades cannot exceed total_trades.",
    ):
        PerformanceSummary(
            total_trades=5,
            winning_trades=4,
            losing_trades=2,
            win_rate=0.8,
            total_pnl=100.0,
            average_pnl=20.0,
            max_drawdown=50.0,
        )


def test_raises_error_when_win_rate_is_negative():
    with pytest.raises(ValueError, match="win_rate cannot be negative."):
        PerformanceSummary(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=-0.1,
            total_pnl=500.0,
            average_pnl=50.0,
            max_drawdown=100.0,
        )


def test_raises_error_when_win_rate_is_greater_than_one():
    with pytest.raises(ValueError, match="win_rate cannot be greater than 1."):
        PerformanceSummary(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=1.1,
            total_pnl=500.0,
            average_pnl=50.0,
            max_drawdown=100.0,
        )


def test_raises_error_when_max_drawdown_is_negative():
    with pytest.raises(ValueError, match="max_drawdown cannot be negative."):
        PerformanceSummary(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=0.6,
            total_pnl=500.0,
            average_pnl=50.0,
            max_drawdown=-100.0,
        )
