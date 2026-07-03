"""
Base Risk Manager Tests
"""

import pytest

from src.risk.base_risk_manager import BaseRiskManager
from src.risk.risk_profile import RiskProfile
from src.risk.trade_plan import TradePlan
from src.strategy.trade_signal import TradeSignal


class DummyRiskManager(BaseRiskManager):
    def plan(
        self,
        signal: TradeSignal,
        risk_profile: RiskProfile,
        entry_price: float,
        stop_loss: float,
    ) -> tuple[TradePlan, ...]:
        return ()


def test_base_risk_manager_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseRiskManager()


def test_dummy_risk_manager_implements_base_risk_manager_contract():
    manager = DummyRiskManager()

    assert isinstance(manager, BaseRiskManager)
    assert manager.plan(None, None, 100.0, 95.0) == ()
