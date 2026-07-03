"""
Base Backtest Engine Tests
"""

import pytest

from src.backtesting.backtest_result import BacktestResult
from src.backtesting.base_backtest_engine import BaseBacktestEngine


class DummyBacktestEngine(BaseBacktestEngine):
    def run(self) -> BacktestResult:
        return BacktestResult(total_trades=0)


def test_base_backtest_engine_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseBacktestEngine()


def test_dummy_backtest_engine_implements_base_backtest_engine_contract():
    engine = DummyBacktestEngine()

    assert isinstance(engine, BaseBacktestEngine)
    assert engine.run() == BacktestResult(total_trades=0)
