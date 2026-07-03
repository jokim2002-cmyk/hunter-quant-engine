"""
Tests for FixedRiskPositionSizer.
"""

import pytest

from src.risk.position_sizing.base_position_sizer import BasePositionSizer
from src.risk.position_sizing.fixed_risk_position_sizer import FixedRiskPositionSizer
from tests.builders.risk.risk_profile_builder import RiskProfileBuilder


def test_fixed_risk_position_sizer_implements_base_position_sizer_contract():
    sizer = FixedRiskPositionSizer()

    assert isinstance(sizer, BasePositionSizer)


def test_calculates_long_position_size_from_fixed_risk():
    risk_profile = RiskProfileBuilder().build()

    position_size = FixedRiskPositionSizer().calculate(
        risk_profile=risk_profile,
        entry_price=100.0,
        stop_loss=95.0,
    )

    assert position_size == 20.0


def test_calculates_short_position_size_from_fixed_risk():
    risk_profile = RiskProfileBuilder().build()

    position_size = FixedRiskPositionSizer().calculate(
        risk_profile=risk_profile,
        entry_price=100.0,
        stop_loss=105.0,
    )

    assert position_size == 20.0


def test_calculates_position_size_with_custom_risk_profile():
    risk_profile = (
        RiskProfileBuilder()
        .with_account_balance(50000.0)
        .with_risk_per_trade(0.02)
        .build()
    )

    position_size = FixedRiskPositionSizer().calculate(
        risk_profile=risk_profile,
        entry_price=250.0,
        stop_loss=240.0,
    )

    assert position_size == 100.0


def test_raises_error_when_entry_price_is_zero():
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(ValueError, match="entry_price must be greater than zero."):
        FixedRiskPositionSizer().calculate(
            risk_profile=risk_profile,
            entry_price=0.0,
            stop_loss=95.0,
        )


def test_raises_error_when_entry_price_is_negative():
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(ValueError, match="entry_price must be greater than zero."):
        FixedRiskPositionSizer().calculate(
            risk_profile=risk_profile,
            entry_price=-100.0,
            stop_loss=95.0,
        )


def test_raises_error_when_stop_loss_is_zero():
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(ValueError, match="stop_loss must be greater than zero."):
        FixedRiskPositionSizer().calculate(
            risk_profile=risk_profile,
            entry_price=100.0,
            stop_loss=0.0,
        )


def test_raises_error_when_stop_loss_is_negative():
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(ValueError, match="stop_loss must be greater than zero."):
        FixedRiskPositionSizer().calculate(
            risk_profile=risk_profile,
            entry_price=100.0,
            stop_loss=-95.0,
        )


def test_raises_error_when_entry_price_and_stop_loss_are_equal():
    risk_profile = RiskProfileBuilder().build()

    with pytest.raises(
        ValueError,
        match="entry_price and stop_loss cannot be equal.",
    ):
        FixedRiskPositionSizer().calculate(
            risk_profile=risk_profile,
            entry_price=100.0,
            stop_loss=100.0,
        )
