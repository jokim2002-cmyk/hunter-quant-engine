"""
Base Trade Level Planner Tests
"""

import pytest

from src.risk.risk_profile import RiskProfile
from src.risk.trade_level_planning.base_trade_level_planner import BaseTradeLevelPlanner
from src.risk.trade_level_planning.trade_levels import TradeLevels
from src.strategy.signal_type import SignalType


class DummyTradeLevelPlanner(BaseTradeLevelPlanner):
    def plan(
        self,
        signal_type: SignalType,
        entry_price: float,
        stop_loss: float,
        risk_profile: RiskProfile,
    ) -> TradeLevels:
        return TradeLevels(
            signal_type=SignalType.LONG,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
        )


def test_base_trade_level_planner_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseTradeLevelPlanner()


def test_dummy_trade_level_planner_implements_base_trade_level_planner_contract():
    planner = DummyTradeLevelPlanner()

    assert isinstance(planner, BaseTradeLevelPlanner)

    result = planner.plan(None, 100.0, 95.0, None)

    assert isinstance(result, TradeLevels)
