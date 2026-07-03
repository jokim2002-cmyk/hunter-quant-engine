"""
Tests for RiskProfileBuilder.
"""

from tests.builders.risk.risk_profile_builder import RiskProfileBuilder


def test_builds_risk_profile_with_defaults():
    profile = RiskProfileBuilder().build()

    assert profile.account_balance == 10000.0
    assert profile.risk_per_trade == 0.01
    assert profile.reward_to_risk == 2.0


def test_builds_risk_profile_with_custom_account_balance():
    profile = RiskProfileBuilder().with_account_balance(25000.0).build()

    assert profile.account_balance == 25000.0


def test_builds_risk_profile_with_custom_risk_per_trade():
    profile = RiskProfileBuilder().with_risk_per_trade(0.02).build()

    assert profile.risk_per_trade == 0.02


def test_builds_risk_profile_with_custom_reward_to_risk():
    profile = RiskProfileBuilder().with_reward_to_risk(3.0).build()

    assert profile.reward_to_risk == 3.0
