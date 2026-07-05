"""
Dynamic Option Strike Selector Tests
"""

from datetime import date, datetime

import pytest

from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.dynamic_option_strike_selector import (
    DynamicOptionStrikeSelector,
)
from src.trade_planning.option_strike_selection_result import (
    OptionStrikeSelectionRejection,
    OptionStrikeSelectionResult,
)


def _signal(signal_type):
    return TradeSignal(
        signal_type=signal_type,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("test signal",),
        created_at=datetime(2026, 7, 3, 10, 15),
    )


def _contract(option_type, strike_price):
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=float(strike_price),
        option_type=option_type,
        lot_size=65,
        symbol=f"NIFTY26JUL{int(strike_price)}{option_type.value}",
    )


def _entry(option_type, strike_price, last_traded_price=100.0):
    return OptionChainEntry(
        contract=_contract(option_type, strike_price),
        last_traded_price=last_traded_price,
        bid_price=last_traded_price - 1.0,
        ask_price=last_traded_price + 1.0,
        volume=10000,
        open_interest=50000,
    )


def _snapshot(entries, underlying_price=24210.0):
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=underlying_price,
        timestamp=datetime(2026, 7, 3, 10, 15),
        entries=tuple(entries),
    )


def test_selector_maps_long_signal_to_ce_and_selects_closest_strike():
    ce_24200 = _entry(OptionType.CE, 24200)
    ce_24300 = _entry(OptionType.CE, 24300)
    pe_24200 = _entry(OptionType.PE, 24200)

    selector = DynamicOptionStrikeSelector()
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24300, pe_24200, ce_24200), 24210.0),
    )

    assert result.has_selection is True
    assert result.selected_entry == ce_24200
    assert result.selected_entry.option_type == OptionType.CE
    assert result.selected_reason == (
        "Selected CE strike closest to underlying price 24210.0"
    )
    assert len(result.rejected_entries) == 2
    assert pe_24200 in tuple(
        rejection.entry for rejection in result.rejected_entries
    )


def test_selector_maps_short_signal_to_pe_and_selects_closest_strike():
    pe_24200 = _entry(OptionType.PE, 24200)
    pe_24100 = _entry(OptionType.PE, 24100)
    ce_24200 = _entry(OptionType.CE, 24200)

    selector = DynamicOptionStrikeSelector()
    result = selector.select(
        signal=_signal(SignalType.SHORT),
        snapshot=_snapshot((pe_24100, ce_24200, pe_24200), 24210.0),
    )

    assert result.has_selection is True
    assert result.selected_entry == pe_24200
    assert result.selected_entry.option_type == OptionType.PE
    assert result.selected_reason == (
        "Selected PE strike closest to underlying price 24210.0"
    )
    assert len(result.rejected_entries) == 2
    assert ce_24200 in tuple(
        rejection.entry for rejection in result.rejected_entries
    )


def test_selector_rejects_all_entries_for_neutral_signal():
    ce_entry = _entry(OptionType.CE, 24200)
    pe_entry = _entry(OptionType.PE, 24200)

    selector = DynamicOptionStrikeSelector()
    result = selector.select(
        signal=_signal(SignalType.NEUTRAL),
        snapshot=_snapshot((ce_entry, pe_entry)),
    )

    assert result.has_selection is False
    assert result.selected_entry is None
    assert result.selected_reason == (
        "Neutral signal does not map to CE or PE option-buy selection"
    )
    assert result.rejection_reasons == (
        "Neutral signal does not allow option-buy selection",
        "Neutral signal does not allow option-buy selection",
    )


def test_selector_returns_no_selection_when_required_option_side_is_missing():
    pe_entry = _entry(OptionType.PE, 24200)

    selector = DynamicOptionStrikeSelector()
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((pe_entry,)),
    )

    assert result.has_selection is False
    assert result.selected_entry is None
    assert result.selected_reason == "No CE entries available for long signal"
    assert result.rejected_entries[0].entry == pe_entry
    assert result.rejected_entries[0].reason == (
        "PE entry rejected because long signal requires CE"
    )


def test_selector_uses_lower_strike_as_deterministic_tie_breaker():
    ce_24200 = _entry(OptionType.CE, 24200)
    ce_24250 = _entry(OptionType.CE, 24250)

    selector = DynamicOptionStrikeSelector()
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24250, ce_24200), 24225.0),
    )

    assert result.selected_entry == ce_24200


def test_option_strike_selection_rejection_requires_reason():
    with pytest.raises(ValueError, match="reason is required"):
        OptionStrikeSelectionRejection(
            entry=_entry(OptionType.CE, 24200),
            reason="",
        )


def test_option_strike_selection_result_normalizes_rejected_entries_tuple():
    rejection = OptionStrikeSelectionRejection(
        entry=_entry(OptionType.PE, 24200),
        reason="wrong side",
    )

    result = OptionStrikeSelectionResult(
        signal=_signal(SignalType.LONG),
        selected_entry=_entry(OptionType.CE, 24200),
        selected_reason="selected",
        rejected_entries=[rejection],
    )

    assert result.rejected_entries == (rejection,)
    assert result.rejection_reasons == ("wrong side",)


def test_option_strike_selection_result_requires_selected_reason():
    with pytest.raises(ValueError, match="selected_reason is required"):
        OptionStrikeSelectionResult(
            signal=_signal(SignalType.LONG),
            selected_entry=None,
            selected_reason="",
            rejected_entries=(),
        )
