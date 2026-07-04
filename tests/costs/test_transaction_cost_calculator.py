"""
Transaction Cost Calculator Tests
"""

from types import SimpleNamespace

import pytest

from src.costs.transaction_cost_calculator import TransactionCostCalculator
from src.costs.transaction_cost_profile import TransactionCostProfile
from src.costs.transaction_cost_profile_preset import (
    COST_PROFILE_FYERS_EQUITY_INTRADAY,
    build_transaction_cost_profile_from_name,
)


def test_transaction_cost_profile_rejects_negative_values():
    with pytest.raises(ValueError):
        TransactionCostProfile(
            brokerage_per_order=-1.0,
        )


def test_transaction_cost_calculator_returns_zero_charges_by_default():
    trade = SimpleNamespace(
        entry_price=100.0,
        exit_price=110.0,
        position_size=10.0,
        pnl=100.0,
    )

    breakdown = TransactionCostCalculator().calculate(trade)

    assert breakdown.gross_pnl == 100.0
    assert breakdown.brokerage == 0.0
    assert breakdown.stt == 0.0
    assert breakdown.exchange_transaction_charge == 0.0
    assert breakdown.sebi_charge == 0.0
    assert breakdown.stamp_duty == 0.0
    assert breakdown.gst == 0.0
    assert breakdown.total_charges == 0.0
    assert breakdown.net_pnl == 100.0


def test_transaction_cost_calculator_calculates_total_charges_and_net_pnl():
    trade = SimpleNamespace(
        entry_price=100.0,
        exit_price=110.0,
        position_size=10.0,
        pnl=100.0,
    )
    profile = TransactionCostProfile(
        brokerage_per_order=20.0,
        stt_rate=0.001,
        exchange_transaction_charge_rate=0.002,
        sebi_charge_rate=0.003,
        stamp_duty_rate=0.004,
        gst_rate=0.18,
    )

    breakdown = TransactionCostCalculator(profile).calculate(trade)

    assert breakdown.gross_pnl == 100.0
    assert breakdown.brokerage == 40.0
    assert breakdown.stt == 1.1
    assert breakdown.exchange_transaction_charge == 4.2
    assert breakdown.sebi_charge == 6.3
    assert breakdown.stamp_duty == 4.0
    assert breakdown.gst == pytest.approx(9.09)
    assert breakdown.total_charges == pytest.approx(64.69)
    assert breakdown.net_pnl == pytest.approx(35.31)


def test_transaction_cost_calculator_uses_percentage_brokerage_when_rate_exists():
    trade = SimpleNamespace(
        entry_price=100.0,
        exit_price=110.0,
        position_size=10.0,
        pnl=100.0,
    )
    profile = TransactionCostProfile(
        brokerage_rate=0.001,
    )

    breakdown = TransactionCostCalculator(profile).calculate(trade)

    assert breakdown.brokerage == 2.1
    assert breakdown.total_charges == 2.1
    assert breakdown.net_pnl == 97.9


def test_transaction_cost_calculator_caps_percentage_brokerage_per_order():
    trade = SimpleNamespace(
        entry_price=100000.0,
        exit_price=110000.0,
        position_size=1.0,
        pnl=10000.0,
    )
    profile = TransactionCostProfile(
        brokerage_rate=0.001,
        brokerage_cap_per_order=20.0,
    )

    breakdown = TransactionCostCalculator(profile).calculate(trade)

    assert breakdown.brokerage == 40.0
    assert breakdown.total_charges == 40.0
    assert breakdown.net_pnl == 9960.0


def test_fyers_equity_intraday_preset_uses_lower_of_percentage_or_cap():
    trade = SimpleNamespace(
        entry_price=114.0,
        exit_price=120.0,
        position_size=33.333333333333336,
        pnl=200.0,
    )
    profile = build_transaction_cost_profile_from_name(
        COST_PROFILE_FYERS_EQUITY_INTRADAY
    )

    breakdown = TransactionCostCalculator(profile).calculate(trade)

    assert breakdown.brokerage == pytest.approx(2.34)
    assert breakdown.stt == pytest.approx(1.0)
    assert breakdown.exchange_transaction_charge == pytest.approx(0.2394522)
    assert breakdown.sebi_charge == pytest.approx(0.0078)
    assert breakdown.stamp_duty == pytest.approx(0.114)
    assert breakdown.gst == pytest.approx(0.465705396)
    assert breakdown.total_charges == pytest.approx(4.166957596)
    assert breakdown.net_pnl == pytest.approx(195.833042404)
