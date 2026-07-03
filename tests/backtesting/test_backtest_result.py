"""
Tests for BacktestResult.
"""

from dataclasses import FrozenInstanceError

import pytest

from src.backtesting.backtest_result import BacktestResult


def test_backtest_result_can_be_created():
    result = BacktestResult(total_trades=0)

    assert result.total_trades == 0


def test_backtest_result_is_immutable():
    result = BacktestResult(total_trades=0)

    with pytest.raises(FrozenInstanceError):
        result.total_trades = 1
