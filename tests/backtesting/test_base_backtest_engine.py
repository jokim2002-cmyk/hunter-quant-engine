"""
Base Backtest Engine Tests
"""

import pytest

from src.backtesting.backtest_result import BacktestResult
from src.backtesting.base_backtest_engine import BaseBacktestEngine
from src.backtesting.performance_summary import PerformanceSummary


class DummyBacktestEngine(BaseBacktestEngine):
    def run(self) -> BacktestResult:
        return BacktestResult(
            trades=(),
            performance_summary=PerformanceSummary(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                average_pnl=0.0,
                max_drawdown=0.0,
            ),
        )


def test_base_backtest_engine_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseBacktestEngine()


def test_dummy_backtest_engine_implements_base_backtest_engine_contract():
    engine = DummyBacktestEngine()

    assert isinstance(engine, BaseBacktestEngine)

    result = engine.run()

    assert isinstance(result, BacktestResult)
    assert result.trades == ()
    assert result.performance_summary.total_trades == 0
