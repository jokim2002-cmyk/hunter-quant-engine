"""
Tests for RiskManager.
"""

from datetime import datetime

import pytest

from src.risk.base_risk_manager import BaseRiskManager
from src.risk.risk_manager import RiskManager
from src.strategy.signal_type import SignalType
from tests.builders.risk.risk_profile_builder import RiskProfileBuilder
from tests.builders.strategy.trade_signal_builder import TradeSignalBuilder


def test_risk_manager_implements_base_risk_manager_contract():
    manager = RiskManager()

    assert isinstance(manager, BaseRiskManager)


def test_creates_long_trade_plan_from_long_signal():
    created_at = datetime(2026, 7, 1)
    signal = TradeSignalBuilder().long().created_at(created_at).build()
    risk_profile = RiskProfileBuilder().build()

    result = RiskManager().plan(
        signal=signal,
        risk_profile=risk_profile,
        entry_price=100.0,
        stop_loss=95.0,
    )

    assert len(result) == 1

    plan = result[0]

    assert plan.signal_type == SignalType.LONG
    assert plan.entry_price == 100.0
    assert plan.stop_loss == 95.0
    assert plan.take_profit == 110.0
    assert plan.position_size == 20.0
    assert plan.risk_amount == 100.0
    assert plan.reward_amount == 200.0
    assert plan.created_at == created_at


def test_creates_short_trade_plan_from_short_signal():
    created_at = datetime(2026, 7, 2)
    signal = TradeSignalBuilder().short().created_at(created_at).build()
    risk_profile = RiskProfileBuilder().build()

    result = RiskManager().plan(
        signal=signal,
        risk_profile=risk_profile,
        entry_price=100.0,
        stop_loss=105.0,
    )

    assert len(result) == 1

    plan = result[0]

    assert plan.signal_type == SignalType.SHORT
    assert plan.entry_price == 100.0
    assert plan.stop_loss == 105.0
    assert plan.take_profit == 90.0
    assert plan.position_size == 20.0
    assert plan.risk_amount == 100.0
    assert plan.reward_amount == 200.0
    assert plan.created_at == created_at


def test_returns_empty_tuple_for_neutral_signal():
    signal = TradeSignalBuilder().neutral().build()
    risk_profile = RiskProfileBuilder().build()

    result = RiskManager().plan(
        signal=signal,
        risk_profile=risk_profile,
        entry_price=100.0,
        stop_loss=95.0,
    )

    assert result == ()


def test_creates_trade_plan_with_custom_risk_profile():
    signal = TradeSignalBuilder().long().build()
    risk_profile = (
        RiskProfileBuilder()
        .with_account_balance(50000.0)
        .with_risk_per_trade(0.02)
        .with_reward_to_risk(3.0)
        .build()
    )

    result = RiskManager().plan(
        signal=signal,
        risk_profile=risk_profile,
        entry_price=200.0,
        stop_loss=190.0,
    )

    plan = result[0]

    assert plan.entry_price == 200.0
    assert plan.stop_loss == 190.0
    assert plan.take_profit == 230.0
    assert plan.position_size == 100.0
    assert plan.risk_amount == 1000.0
    assert plan.reward_amount == 3000.0


def test_raises_error_when_long_signal_has_invalid_stop_loss():
    signal = TradeSignalBuilder().long().build()
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(
        ValueError,
        match="Long trade stop_loss must be below entry_price.",
    ):
        RiskManager().plan(
            signal=signal,
            risk_profile=risk_profile,
            entry_price=100.0,
            stop_loss=105.0,
        )


def test_raises_error_when_short_signal_has_invalid_stop_loss():
    signal = TradeSignalBuilder().short().build()
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(
        ValueError,
        match="Short trade stop_loss must be above entry_price.",
    ):
        RiskManager().plan(
            signal=signal,
            risk_profile=risk_profile,
            entry_price=100.0,
            stop_loss=95.0,
        )
