"""
Option Buy Robustness Controls Tests
"""

from datetime import date, datetime

import pytest

from src.costs.transaction_cost_calculator import TransactionCostCalculator
from src.costs.transaction_cost_profile import TransactionCostProfile
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.dynamic_option_strike_selector import (
    DynamicOptionStrikeSelector,
    OptionLiquidityFilterConfig,
)
from src.trade_planning.fixed_percent_option_premium_trade_level_planner import (
    FixedPercentOptionPremiumTradeLevelPlanner,
)
from src.trade_planning.option_buy_trade_plan_builder import OptionBuyTradePlanBuilder
from src.trade_planning.option_premium_trade_level_config import (
    OptionPremiumTradeLevelConfig,
)
from src.trade_planning.option_premium_trade_levels import OptionPremiumTradeLevels
from src.trade_planning.option_strike_selection_result import (
    OptionStrikeSelectionResult,
)


def _signal(signal_type=SignalType.LONG):
    return TradeSignal(
        signal_type=signal_type,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("robustness test signal",),
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


def _entry(
    option_type=OptionType.CE,
    strike_price=24200.0,
    last_traded_price=100.0,
    bid_price=99.0,
    ask_price=100.0,
    volume=10000,
    open_interest=50000,
):
    return OptionChainEntry(
        contract=_contract(option_type=option_type, strike_price=strike_price),
        last_traded_price=last_traded_price,
        bid_price=bid_price,
        ask_price=ask_price,
        volume=volume,
        open_interest=open_interest,
    )


def _snapshot(*entries):
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=datetime(2026, 7, 6, 10, 15),
        entries=entries,
    )


def _selection_result(entry):
    return OptionStrikeSelectionResult(
        signal=_signal(),
        selected_entry=entry,
        selected_reason="selected",
        rejected_entries=(),
    )


def _premium_levels(entry):
    return OptionPremiumTradeLevels(
        entry=entry,
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        premium_source="ask_price",
    )


def test_selector_rejects_zero_volume_when_min_volume_enabled():
    entry = _entry(volume=0)
    selector = DynamicOptionStrikeSelector(
        liquidity_config=OptionLiquidityFilterConfig(min_volume=1)
    )

    result = selector.select(_signal(), _snapshot(entry))

    assert not result.has_selection
    assert result.rejection_reasons == (
        "CE strike 24200.0 rejected because volume below minimum 1",
    )


def test_entry_slippage_is_applied_before_levels_are_planned():
    planner = FixedPercentOptionPremiumTradeLevelPlanner(
        config=OptionPremiumTradeLevelConfig(
            stop_loss_percent=0.30,
            target_percent=0.60,
            entry_slippage_percent=0.01,
        )
    )

    levels = planner.plan(_entry(ask_price=100.0))

    assert levels.entry_premium == pytest.approx(101.0)
    assert levels.stop_loss_premium == pytest.approx(70.7)
    assert levels.target_premium == pytest.approx(161.6)
    assert levels.premium_source == "ask_price+entry_slippage_0.01"


def test_builder_rejects_plan_when_estimated_net_reward_is_below_minimum():
    entry = _entry()
    builder = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=TransactionCostCalculator(
            TransactionCostProfile(brokerage_per_order=20.0)
        ),
        min_estimated_net_reward=10000.0,
    )

    result = builder.build(
        selection_result=_selection_result(entry),
        premium_levels=_premium_levels(entry),
        underlying_price=24210.0,
    )

    assert not result.has_plan
    assert result.rejection_reasons == (
        "estimated net reward below minimum 10000.0",
    )


def test_builder_accepts_plan_when_estimated_net_reward_meets_minimum():
    entry = _entry()
    builder = OptionBuyTradePlanBuilder(
        lots=1,
        cost_calculator=TransactionCostCalculator(
            TransactionCostProfile(brokerage_per_order=20.0)
        ),
        min_estimated_net_reward=1000.0,
    )

    result = builder.build(
        selection_result=_selection_result(entry),
        premium_levels=_premium_levels(entry),
        underlying_price=24210.0,
    )

    assert result.has_plan
    assert result.plan.estimated_charges > 0
