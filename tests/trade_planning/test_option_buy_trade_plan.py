"""
Option Buy Trade Plan Tests
"""

from datetime import date, datetime

import pytest

from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import (
    OptionBuyTradePlanStatus,
)


def _signal(signal_type=SignalType.LONG):
    return TradeSignal(
        signal_type=signal_type,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("test signal",),
        created_at=datetime(2026, 7, 6, 10, 15),
    )


def _contract(option_type=OptionType.CE):
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=option_type,
        lot_size=65,
        symbol=f"NIFTY26JUL24200{option_type.value}",
    )


def _entry(option_type=OptionType.CE):
    return OptionChainEntry(
        contract=_contract(option_type),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )


def _plan(**overrides):
    values = {
        "signal": _signal(),
        "entry": _entry(),
        "action": OptionAction.BUY,
        "underlying_price": 24210.0,
        "entry_premium": 100.0,
        "stop_loss_premium": 70.0,
        "target_premium": 160.0,
        "lots": 2,
        "estimated_charges": 40.0,
        "status": OptionBuyTradePlanStatus.APPROVED,
        "rejection_reasons": (),
    }
    values.update(overrides)
    return OptionBuyTradePlan(**values)


def test_stores_approved_ce_buy_trade_plan_fields():
    signal = _signal(SignalType.LONG)
    entry = _entry(OptionType.CE)

    plan = _plan(signal=signal, entry=entry)

    assert plan.signal == signal
    assert plan.entry == entry
    assert plan.action == OptionAction.BUY
    assert plan.underlying_price == 24210.0
    assert plan.entry_premium == 100.0
    assert plan.stop_loss_premium == 70.0
    assert plan.target_premium == 160.0
    assert plan.lots == 2
    assert plan.estimated_charges == 40.0
    assert plan.status == OptionBuyTradePlanStatus.APPROVED
    assert plan.rejection_reasons == ()


def test_stores_approved_pe_buy_trade_plan_fields():
    signal = _signal(SignalType.SHORT)
    entry = _entry(OptionType.PE)

    plan = _plan(signal=signal, entry=entry)

    assert plan.signal.signal_type == SignalType.SHORT
    assert plan.entry.option_type == OptionType.PE
    assert plan.action == OptionAction.BUY
    assert plan.status == OptionBuyTradePlanStatus.APPROVED


def test_action_must_be_buy():
    with pytest.raises(ValueError, match="action must be OptionAction.BUY"):
        _plan(action="SELL")


def test_validates_entry_premium():
    with pytest.raises(ValueError, match="entry_premium must be greater than 0"):
        _plan(entry_premium=0)


def test_validates_stop_loss_premium():
    with pytest.raises(
        ValueError,
        match="stop_loss_premium must be greater than 0",
    ):
        _plan(stop_loss_premium=0)


def test_validates_stop_loss_below_entry():
    with pytest.raises(
        ValueError,
        match="stop_loss_premium must be below entry_premium",
    ):
        _plan(stop_loss_premium=100.0)


def test_validates_target_above_entry():
    with pytest.raises(
        ValueError,
        match="target_premium must be above entry_premium",
    ):
        _plan(target_premium=100.0)


def test_validates_lots():
    with pytest.raises(ValueError, match="lots must be greater than 0"):
        _plan(lots=0)


def test_validates_estimated_charges():
    with pytest.raises(ValueError, match="estimated_charges cannot be negative"):
        _plan(estimated_charges=-1.0)


def test_calculates_quantity():
    assert _plan().quantity == 130


def test_calculates_gross_risk():
    assert _plan().gross_risk == 3900.0


def test_calculates_gross_reward():
    assert _plan().gross_reward == 7800.0


def test_calculates_max_loss():
    assert _plan().max_loss == 3940.0


def test_calculates_estimated_net_reward():
    assert _plan().estimated_net_reward == 7760.0


def test_calculates_risk_reward_ratio():
    assert _plan().risk_reward_ratio == pytest.approx(7760.0 / 3940.0)


def test_normalizes_rejection_reasons_to_tuple():
    plan = _plan(
        status=OptionBuyTradePlanStatus.REJECTED,
        rejection_reasons=["liquidity filter failed"],
    )

    assert plan.rejection_reasons == ("liquidity filter failed",)


def test_approved_plan_rejects_rejection_reasons():
    with pytest.raises(
        ValueError,
        match="approved plan should not contain rejection reasons",
    ):
        _plan(rejection_reasons=("liquidity filter failed",))


def test_rejected_plan_requires_rejection_reason():
    with pytest.raises(
        ValueError,
        match="rejected plan should contain at least one rejection reason",
    ):
        _plan(status=OptionBuyTradePlanStatus.REJECTED)
