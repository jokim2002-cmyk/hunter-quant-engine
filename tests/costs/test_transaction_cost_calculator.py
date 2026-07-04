"""
Transaction Cost Calculator Tests
"""

from types import SimpleNamespace

import pytest

from src.costs.transaction_cost_calculator import TransactionCostCalculator
from src.costs.transaction_cost_profile import TransactionCostProfile


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
