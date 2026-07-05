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
def test_transaction_cost_profile_supports_clearing_and_ipft_rates():
    from src.costs.transaction_cost_profile import TransactionCostProfile

    profile = TransactionCostProfile(
        clearing_charge_rate=0.00009,
        investor_protection_fund_rate=0.0000001,
    )

    assert profile.clearing_charge_rate == 0.00009
    assert profile.investor_protection_fund_rate == 0.0000001


def test_transaction_cost_profile_rejects_negative_extended_rates():
    import pytest

    from src.costs.transaction_cost_profile import TransactionCostProfile

    invalid_profiles = (
        (
            {"clearing_charge_rate": -0.00001},
            "clearing_charge_rate cannot be negative",
        ),
        (
            {"investor_protection_fund_rate": -0.00001},
            "investor_protection_fund_rate cannot be negative",
        ),
    )

    for kwargs, error_message in invalid_profiles:
        with pytest.raises(ValueError, match=error_message):
            TransactionCostProfile(**kwargs)


def test_calculator_includes_clearing_and_ipft_in_total_charges_and_gst():
    import pytest
    from types import SimpleNamespace

    from src.costs.transaction_cost_calculator import TransactionCostCalculator
    from src.costs.transaction_cost_profile import TransactionCostProfile

    profile = TransactionCostProfile(
        brokerage_per_order=20.0,
        exchange_transaction_charge_rate=0.0001,
        sebi_charge_rate=0.000001,
        clearing_charge_rate=0.00009,
        investor_protection_fund_rate=0.0000001,
        gst_rate=0.18,
    )
    calculator = TransactionCostCalculator(profile)
    trade = SimpleNamespace(
        entry_price=100.0,
        exit_price=120.0,
        position_size=65,
        pnl=1300.0,
    )

    breakdown = calculator.calculate(trade)

    total_turnover = 14300.0
    expected_exchange = total_turnover * 0.0001
    expected_sebi = total_turnover * 0.000001
    expected_clearing = total_turnover * 0.00009
    expected_ipft = total_turnover * 0.0000001
    expected_gst = (
        40.0
        + expected_exchange
        + expected_sebi
        + expected_clearing
        + expected_ipft
    ) * 0.18

    assert breakdown.brokerage == 40.0
    assert breakdown.exchange_transaction_charge == pytest.approx(expected_exchange)
    assert breakdown.sebi_charge == pytest.approx(expected_sebi)
    assert breakdown.clearing_charge == pytest.approx(expected_clearing)
    assert breakdown.investor_protection_fund == pytest.approx(expected_ipft)
    assert breakdown.gst == pytest.approx(expected_gst)


def test_fyers_nifty_options_intraday_profile_is_supported():
    from src.costs.transaction_cost_profile_preset import (
        COST_PROFILE_FYERS_NIFTY_OPTIONS_INTRADAY,
        build_transaction_cost_profile_from_name,
        supported_transaction_cost_profile_names,
    )

    assert (
        COST_PROFILE_FYERS_NIFTY_OPTIONS_INTRADAY
        in supported_transaction_cost_profile_names()
    )

    profile = build_transaction_cost_profile_from_name(
        COST_PROFILE_FYERS_NIFTY_OPTIONS_INTRADAY
    )

    assert profile.brokerage_per_order == 20.0
    assert profile.stt_rate == 0.0015
    assert profile.exchange_transaction_charge_rate == 0.000355299
    assert profile.sebi_charge_rate == 0.000001
    assert profile.stamp_duty_rate == 0.00003
    assert profile.clearing_charge_rate == 0.00009
    assert profile.investor_protection_fund_rate == 0.0000001
    assert profile.gst_rate == 0.18


def test_fyers_nifty_options_intraday_round_trip_charge_breakdown():
    import pytest
    from types import SimpleNamespace

    from src.costs.transaction_cost_calculator import TransactionCostCalculator
    from src.costs.transaction_cost_profile_preset import (
        COST_PROFILE_FYERS_NIFTY_OPTIONS_INTRADAY,
        build_transaction_cost_profile_from_name,
    )

    profile = build_transaction_cost_profile_from_name(
        COST_PROFILE_FYERS_NIFTY_OPTIONS_INTRADAY
    )
    calculator = TransactionCostCalculator(profile)
    trade = SimpleNamespace(
        entry_price=100.0,
        exit_price=120.0,
        position_size=65,
        pnl=1300.0,
    )

    breakdown = calculator.calculate(trade)

    entry_turnover = 6500.0
    exit_turnover = 7800.0
    total_turnover = 14300.0

    expected_brokerage = 40.0
    expected_stt = exit_turnover * 0.0015
    expected_exchange = total_turnover * 0.000355299
    expected_sebi = total_turnover * 0.000001
    expected_stamp = entry_turnover * 0.00003
    expected_clearing = total_turnover * 0.00009
    expected_ipft = total_turnover * 0.0000001
    expected_gst = (
        expected_brokerage
        + expected_exchange
        + expected_sebi
        + expected_clearing
        + expected_ipft
    ) * 0.18
    expected_total_charges = (
        expected_brokerage
        + expected_stt
        + expected_exchange
        + expected_sebi
        + expected_stamp
        + expected_clearing
        + expected_ipft
        + expected_gst
    )

    assert breakdown.gross_pnl == 1300.0
    assert breakdown.brokerage == pytest.approx(expected_brokerage)
    assert breakdown.stt == pytest.approx(expected_stt)
    assert breakdown.exchange_transaction_charge == pytest.approx(expected_exchange)
    assert breakdown.sebi_charge == pytest.approx(expected_sebi)
    assert breakdown.stamp_duty == pytest.approx(expected_stamp)
    assert breakdown.clearing_charge == pytest.approx(expected_clearing)
    assert breakdown.investor_protection_fund == pytest.approx(expected_ipft)
    assert breakdown.gst == pytest.approx(expected_gst)
    assert breakdown.total_charges == pytest.approx(expected_total_charges)
    assert breakdown.net_pnl == pytest.approx(1300.0 - expected_total_charges)
