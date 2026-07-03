"""
Tests for RiskProfile.
"""

from dataclasses import FrozenInstanceError

import pytest

from src.risk.risk_profile import RiskProfile


def test_risk_profile_can_be_created():
    profile = RiskProfile(
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
    )

    assert profile.account_balance == 10000.0
    assert profile.risk_per_trade == 0.01
    assert profile.reward_to_risk == 2.0


def test_risk_profile_is_immutable():
    profile = RiskProfile(
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
    )

    with pytest.raises(FrozenInstanceError):
        profile.account_balance = 20000.0


def test_risk_amount_returns_account_balance_multiplied_by_risk_per_trade():
    profile = RiskProfile(
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
    )

    assert profile.risk_amount() == 100.0


def test_raises_error_when_account_balance_is_zero():
    with pytest.raises(ValueError, match="account_balance must be greater than zero."):
        RiskProfile(
            account_balance=0.0,
            risk_per_trade=0.01,
            reward_to_risk=2.0,
        )


def test_raises_error_when_account_balance_is_negative():
    with pytest.raises(ValueError, match="account_balance must be greater than zero."):
        RiskProfile(
            account_balance=-1000.0,
            risk_per_trade=0.01,
            reward_to_risk=2.0,
        )


def test_raises_error_when_risk_per_trade_is_zero():
    with pytest.raises(ValueError, match="risk_per_trade must be greater than zero."):
        RiskProfile(
            account_balance=10000.0,
            risk_per_trade=0.0,
            reward_to_risk=2.0,
        )


def test_raises_error_when_risk_per_trade_is_negative():
    with pytest.raises(ValueError, match="risk_per_trade must be greater than zero."):
        RiskProfile(
            account_balance=10000.0,
            risk_per_trade=-0.01,
            reward_to_risk=2.0,
        )


def test_raises_error_when_risk_per_trade_is_greater_than_one():
    with pytest.raises(
        ValueError,
        match="risk_per_trade must be less than or equal to 1.",
    ):
        RiskProfile(
            account_balance=10000.0,
            risk_per_trade=1.01,
            reward_to_risk=2.0,
        )


def test_raises_error_when_reward_to_risk_is_zero():
    with pytest.raises(ValueError, match="reward_to_risk must be greater than zero."):
        RiskProfile(
            account_balance=10000.0,
            risk_per_trade=0.01,
            reward_to_risk=0.0,
        )


def test_raises_error_when_reward_to_risk_is_negative():
    with pytest.raises(ValueError, match="reward_to_risk must be greater than zero."):
        RiskProfile(
            account_balance=10000.0,
            risk_per_trade=0.01,
            reward_to_risk=-2.0,
        )
