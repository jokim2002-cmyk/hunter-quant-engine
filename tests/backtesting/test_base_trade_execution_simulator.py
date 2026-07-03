"""
Base Trade Execution Simulator Tests
"""

import pytest

from src.backtesting.base_trade_execution_simulator import (
    BaseTradeExecutionSimulator,
)


class DummyTradeExecutionSimulator(BaseTradeExecutionSimulator):
    def simulate(self, trade_plan, candles):
        return None


def test_base_trade_execution_simulator_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseTradeExecutionSimulator()


def test_dummy_trade_execution_simulator_implements_contract():
    simulator = DummyTradeExecutionSimulator()

    assert isinstance(simulator, BaseTradeExecutionSimulator)
    assert simulator.simulate(None, ()) is None
