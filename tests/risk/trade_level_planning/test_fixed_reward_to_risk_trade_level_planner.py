"""
Tests for FixedRewardToRiskTradeLevelPlanner.
"""

import pytest

from src.risk.trade_level_planning.base_trade_level_planner import BaseTradeLevelPlanner
from src.risk.trade_level_planning.fixed_reward_to_risk_trade_level_planner import (
    FixedRewardToRiskTradeLevelPlanner,
)
from src.strategy.signal_type import SignalType
from tests.builders.risk.risk_profile_builder import RiskProfileBuilder


def test_fixed_reward_to_risk_trade_level_planner_implements_base_contract():
    planner = FixedRewardToRiskTradeLevelPlanner()

    assert isinstance(planner, BaseTradeLevelPlanner)


def test_plans_long_trade_levels_using_reward_to_risk():
    risk_profile = RiskProfileBuilder().with_reward_to_risk(2.0).build()

    levels = FixedRewardToRiskTradeLevelPlanner().plan(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        stop_loss=95.0,
        risk_profile=risk_profile,
    )

    assert levels.signal_type == SignalType.LONG
    assert levels.entry_price == 100.0
    assert levels.stop_loss == 95.0
    assert levels.take_profit == 110.0


def test_plans_short_trade_levels_using_reward_to_risk():
    risk_profile = RiskProfileBuilder().with_reward_to_risk(2.0).build()

    levels = FixedRewardToRiskTradeLevelPlanner().plan(
        signal_type=SignalType.SHORT,
        entry_price=100.0,
        stop_loss=105.0,
        risk_profile=risk_profile,
    )

    assert levels.signal_type == SignalType.SHORT
    assert levels.entry_price == 100.0
    assert levels.stop_loss == 105.0
    assert levels.take_profit == 90.0


def test_plans_trade_levels_using_custom_reward_to_risk():
    risk_profile = RiskProfileBuilder().with_reward_to_risk(3.0).build()

    levels = FixedRewardToRiskTradeLevelPlanner().plan(
        signal_type=SignalType.LONG,
        entry_price=200.0,
        stop_loss=190.0,
        risk_profile=risk_profile,
    )

    assert levels.take_profit == 230.0


def test_raises_error_for_neutral_signal():
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(
        ValueError,
        match="TradeLevels cannot be created for neutral signals.",
    ):
        FixedRewardToRiskTradeLevelPlanner().plan(
            signal_type=SignalType.NEUTRAL,
            entry_price=100.0,
            stop_loss=95.0,
            risk_profile=risk_profile,
        )


def test_raises_error_when_long_stop_loss_is_invalid():
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(
        ValueError,
        match="Long trade stop_loss must be below entry_price.",
    ):
        FixedRewardToRiskTradeLevelPlanner().plan(
            signal_type=SignalType.LONG,
            entry_price=100.0,
            stop_loss=105.0,
            risk_profile=risk_profile,
        )


def test_raises_error_when_short_stop_loss_is_invalid():
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(
        ValueError,
        match="Short trade stop_loss must be above entry_price.",
    ):
        FixedRewardToRiskTradeLevelPlanner().plan(
            signal_type=SignalType.SHORT,
            entry_price=100.0,
            stop_loss=95.0,
            risk_profile=risk_profile,
        )
