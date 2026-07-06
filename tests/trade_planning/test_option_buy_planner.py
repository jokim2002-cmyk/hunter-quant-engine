"""
Option Buy Planner Tests
"""

from datetime import date, datetime

from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_planner import OptionBuyPlanner
from src.trade_planning.option_buy_trade_plan_build_result import (
    OptionBuyTradePlanBuildResult,
)
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus
from src.trade_planning.option_premium_trade_levels import OptionPremiumTradeLevels
from src.trade_planning.option_strike_selection_result import (
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


def _entry(option_type=OptionType.CE, strike_price=24200.0, ask_price=100.0):
    return OptionChainEntry(
        contract=_contract(option_type=option_type, strike_price=strike_price),
        last_traded_price=99.0,
        bid_price=98.0,
        ask_price=ask_price,
        volume=10000,
        open_interest=50000,
    )


def _snapshot(entries=None, underlying_price=24210.0):
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=underlying_price,
        timestamp=datetime(2026, 7, 6, 10, 15),
        entries=tuple(entries or (_entry(OptionType.CE), _entry(OptionType.PE))),
    )


class _FixedSelector:
    def __init__(self, selection_result):
        self.selection_result = selection_result

    def select(self, signal, snapshot):
        return self.selection_result


class _FixedPremiumPlanner:
    def __init__(self, entry_premium=120.0):
        self.entry_premium = entry_premium

    def plan(self, entry):
        return OptionPremiumTradeLevels(
            entry=entry,
            entry_premium=self.entry_premium,
            stop_loss_premium=self.entry_premium * 0.7,
            target_premium=self.entry_premium * 1.6,
            premium_source="test",
        )


class _FailingPremiumPlanner:
    def plan(self, entry):
        raise ValueError("bad premium levels")


class _RejectingTradePlanBuilder:
    def build(self, selection_result, premium_levels, underlying_price):
        return OptionBuyTradePlanBuildResult(
            plan=None,
            rejection_reasons=("custom builder rejection",),
        )


def _selected_result(entry, signal=None):
    return OptionStrikeSelectionResult(
        signal=signal or _signal(),
        selected_entry=entry,
        selected_reason="selected",
        rejected_entries=(),
    )


def test_default_planner_builds_approved_long_to_ce_plan():
    result = OptionBuyPlanner().plan(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot(),
    )

    assert result.has_plan is True
    assert result.plan.entry.option_type == OptionType.CE
    assert result.plan.status == OptionBuyTradePlanStatus.APPROVED


def test_default_planner_builds_approved_short_to_pe_plan():
    result = OptionBuyPlanner().plan(
        signal=_signal(SignalType.SHORT),
        snapshot=_snapshot(),
    )

    assert result.has_plan is True
    assert result.plan.entry.option_type == OptionType.PE
    assert result.plan.status == OptionBuyTradePlanStatus.APPROVED


def test_neutral_signal_returns_no_plan():
    result = OptionBuyPlanner().plan(
        signal=_signal(SignalType.NEUTRAL),
        snapshot=_snapshot(),
    )

    assert result.has_plan is False
    assert result.rejection_reasons == (
        "Neutral signal does not allow option-buy selection",
        "Neutral signal does not allow option-buy selection",
    )


def test_planner_returns_rejection_when_selector_returns_no_selected_entry():
    snapshot = _snapshot(entries=(_entry(OptionType.PE),))

    result = OptionBuyPlanner().plan(
        signal=_signal(SignalType.LONG),
        snapshot=snapshot,
    )

    assert result.has_plan is False
    assert result.rejection_reasons == (
        "PE entry rejected because long signal requires CE",
    )


def test_planner_returns_rejection_when_premium_level_planner_fails():
    result = OptionBuyPlanner(
        premium_level_planner=_FailingPremiumPlanner(),
    ).plan(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot(),
    )

    assert result.has_plan is False
    assert result.rejection_reasons == (
        "premium level planning failed: bad premium levels",
    )


def test_planner_copies_underlying_price_into_final_plan():
    result = OptionBuyPlanner().plan(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot(underlying_price=24321.0),
    )

    assert result.plan.underlying_price == 24321.0


def test_planner_uses_default_one_lot():
    result = OptionBuyPlanner().plan(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot(),
    )

    assert result.plan.lots == 1
    assert result.plan.quantity == 65


def test_planner_allows_injected_selector():
    pe_entry = _entry(OptionType.PE)
    selector = _FixedSelector(
        selection_result=_selected_result(
            entry=pe_entry,
            signal=_signal(SignalType.SHORT),
        )
    )

    result = OptionBuyPlanner(strike_selector=selector).plan(
        signal=_signal(SignalType.SHORT),
        snapshot=_snapshot(),
    )

    assert result.has_plan is True
    assert result.plan.entry == pe_entry


def test_planner_allows_injected_premium_planner():
    result = OptionBuyPlanner(
        premium_level_planner=_FixedPremiumPlanner(entry_premium=120.0),
    ).plan(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot(),
    )

    assert result.has_plan is True
    assert result.plan.entry_premium == 120.0


def test_planner_allows_injected_trade_plan_builder():
    result = OptionBuyPlanner(
        trade_plan_builder=_RejectingTradePlanBuilder(),
    ).plan(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot(),
    )

    assert result.has_plan is False
    assert result.rejection_reasons == ("custom builder rejection",)


def test_final_approved_plan_has_buy_action():
    result = OptionBuyPlanner().plan(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot(),
    )

    assert result.plan.action == OptionAction.BUY


def test_final_approved_plan_has_status_approved():
    result = OptionBuyPlanner().plan(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot(),
    )

    assert result.plan.status == OptionBuyTradePlanStatus.APPROVED


def test_final_rejected_result_has_plan_false():
    result = OptionBuyPlanner().plan(
        signal=_signal(SignalType.NEUTRAL),
        snapshot=_snapshot(),
    )

    assert result.has_plan is False
