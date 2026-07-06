"""
Option Buy Trade Plan Builder Tests
"""

from datetime import date, datetime

import pytest

from src.costs.transaction_cost_calculator import TransactionCostCalculator
from src.costs.transaction_cost_profile import TransactionCostProfile
from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan_build_result import (
    OptionBuyTradePlanBuildResult,
)
from src.trade_planning.option_buy_trade_plan_builder import OptionBuyTradePlanBuilder
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus
from src.trade_planning.option_premium_trade_levels import OptionPremiumTradeLevels
from src.trade_planning.option_strike_selection_result import (
    OptionStrikeSelectionRejection,
    OptionStrikeSelectionResult,
)


def _signal(signal_type=SignalType.LONG):
    return TradeSignal(
        signal_type=signal_type,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("test signal",),
        created_at=datetime(2026, 7, 6, 10, 15),
    )


def _contract(option_type=OptionType.CE, strike_price=24200.0):
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=strike_price,
        option_type=option_type,
        lot_size=65,
        symbol=f"NIFTY26JUL{int(strike_price)}{option_type.value}",
    )


def _entry(option_type=OptionType.CE, strike_price=24200.0):
    return OptionChainEntry(
        contract=_contract(option_type=option_type, strike_price=strike_price),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )


def _selection_result(entry=None, signal=None):
    selected_entry = entry or _entry()
    return OptionStrikeSelectionResult(
        signal=signal or _signal(),
        selected_entry=selected_entry,
        selected_reason="selected",
        rejected_entries=(),
    )


def _premium_levels(entry=None):
    return OptionPremiumTradeLevels(
        entry=entry or _entry(),
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        premium_source="ask_price",
    )


def _cost_calculator():
    return TransactionCostCalculator(
        profile=TransactionCostProfile(brokerage_per_order=1.0)
    )


def test_build_result_requires_rejection_reason_when_plan_missing():
    with pytest.raises(
        ValueError,
        match="rejection_reasons are required when plan is missing",
    ):
        OptionBuyTradePlanBuildResult(plan=None)


def test_build_result_rejects_rejection_reasons_when_plan_exists():
    entry = _entry()
    plan = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=_cost_calculator(),
    ).build(
        selection_result=_selection_result(entry=entry),
        premium_levels=_premium_levels(entry=entry),
        underlying_price=24210.0,
    ).plan

    with pytest.raises(
        ValueError,
        match="rejection_reasons must be empty when plan exists",
    ):
        OptionBuyTradePlanBuildResult(
            plan=plan,
            rejection_reasons=("unexpected reason",),
        )


def test_build_result_has_plan_property():
    rejection_result = OptionBuyTradePlanBuildResult(
        plan=None,
        rejection_reasons=("no selection",),
    )

    assert rejection_result.has_plan is False


def test_builder_validates_lots():
    with pytest.raises(ValueError, match="lots must be greater than 0"):
        OptionBuyTradePlanBuilder(lots=0)


def test_builder_returns_rejection_result_when_strike_selection_has_no_entry():
    rejected_entry = _entry(OptionType.PE)
    selection_result = OptionStrikeSelectionResult(
        signal=_signal(),
        selected_entry=None,
        selected_reason="No CE entries passed filters",
        rejected_entries=(
            OptionStrikeSelectionRejection(
                entry=rejected_entry,
                reason="PE entry rejected because long signal requires CE",
            ),
        ),
    )

    result = OptionBuyTradePlanBuilder(lots=1).build(
        selection_result=selection_result,
        premium_levels=None,
        underlying_price=24210.0,
    )

    assert result.has_plan is False
    assert result.rejection_reasons == (
        "PE entry rejected because long signal requires CE",
    )


def test_builder_uses_selected_reason_when_no_rejection_reasons_exist():
    selection_result = OptionStrikeSelectionResult(
        signal=_signal(),
        selected_entry=None,
        selected_reason="No CE entries available for long signal",
        rejected_entries=(),
    )

    result = OptionBuyTradePlanBuilder(lots=1).build(
        selection_result=selection_result,
        premium_levels=None,
        underlying_price=24210.0,
    )

    assert result.rejection_reasons == ("No CE entries available for long signal",)


def test_builder_rejects_missing_premium_levels():
    entry = _entry()

    result = OptionBuyTradePlanBuilder(lots=1).build(
        selection_result=_selection_result(entry=entry),
        premium_levels=None,
        underlying_price=24210.0,
    )

    assert result.has_plan is False
    assert result.rejection_reasons == (
        "premium levels are required to build option-buy trade plan",
    )


def test_builder_rejects_premium_levels_for_different_entry():
    selected_entry = _entry(strike_price=24200.0)
    different_entry = _entry(strike_price=24300.0)

    result = OptionBuyTradePlanBuilder(lots=1).build(
        selection_result=_selection_result(entry=selected_entry),
        premium_levels=_premium_levels(entry=different_entry),
        underlying_price=24210.0,
    )

    assert result.has_plan is False
    assert result.rejection_reasons == (
        "premium levels entry must match selected option entry",
    )


def test_builder_builds_approved_ce_buy_trade_plan():
    entry = _entry(OptionType.CE)

    result = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=_cost_calculator(),
    ).build(
        selection_result=_selection_result(entry=entry),
        premium_levels=_premium_levels(entry=entry),
        underlying_price=24210.0,
    )

    assert result.has_plan is True
    assert result.plan.status == OptionBuyTradePlanStatus.APPROVED
    assert result.plan.entry.option_type == OptionType.CE


def test_builder_builds_approved_pe_buy_trade_plan():
    entry = _entry(OptionType.PE)

    result = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=_cost_calculator(),
    ).build(
        selection_result=_selection_result(entry=entry, signal=_signal(SignalType.SHORT)),
        premium_levels=_premium_levels(entry=entry),
        underlying_price=24210.0,
    )

    assert result.has_plan is True
    assert result.plan.status == OptionBuyTradePlanStatus.APPROVED
    assert result.plan.entry.option_type == OptionType.PE


def test_builder_sets_buy_action_only():
    entry = _entry()

    result = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=_cost_calculator(),
    ).build(
        selection_result=_selection_result(entry=entry),
        premium_levels=_premium_levels(entry=entry),
        underlying_price=24210.0,
    )

    assert result.plan.action == OptionAction.BUY


def test_builder_copies_signal_and_selected_entry():
    signal = _signal()
    entry = _entry()

    result = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=_cost_calculator(),
    ).build(
        selection_result=_selection_result(entry=entry, signal=signal),
        premium_levels=_premium_levels(entry=entry),
        underlying_price=24210.0,
    )

    assert result.plan.signal == signal
    assert result.plan.entry == entry


def test_builder_copies_entry_sl_target_premiums():
    entry = _entry()

    result = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=_cost_calculator(),
    ).build(
        selection_result=_selection_result(entry=entry),
        premium_levels=_premium_levels(entry=entry),
        underlying_price=24210.0,
    )

    assert result.plan.entry_premium == 100.0
    assert result.plan.stop_loss_premium == 70.0
    assert result.plan.target_premium == 160.0


def test_builder_calculates_quantity_through_option_buy_trade_plan():
    entry = _entry()

    result = OptionBuyTradePlanBuilder(
        lots=2,
        cost_calculator=_cost_calculator(),
    ).build(
        selection_result=_selection_result(entry=entry),
        premium_levels=_premium_levels(entry=entry),
        underlying_price=24210.0,
    )

    assert result.plan.quantity == 130


def test_builder_estimates_charges_using_injected_cost_calculator_profile():
    entry = _entry()

    result = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=_cost_calculator(),
    ).build(
        selection_result=_selection_result(entry=entry),
        premium_levels=_premium_levels(entry=entry),
        underlying_price=24210.0,
    )

    assert result.plan.estimated_charges == 2.0


def test_builder_produces_approved_plan_with_no_rejection_reasons():
    entry = _entry()

    result = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=_cost_calculator(),
    ).build(
        selection_result=_selection_result(entry=entry),
        premium_levels=_premium_levels(entry=entry),
        underlying_price=24210.0,
    )

    assert result.plan.status == OptionBuyTradePlanStatus.APPROVED
    assert result.plan.rejection_reasons == ()
    assert result.rejection_reasons == ()
