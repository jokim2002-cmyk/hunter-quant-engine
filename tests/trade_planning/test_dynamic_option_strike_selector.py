"""
Dynamic Option Strike Selector Tests
"""

from datetime import date, datetime

import pytest

from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_greeks import OptionGreeks
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.dynamic_option_strike_selector import (
    DynamicOptionStrikeSelector,
    OptionGreekFilterConfig,
    OptionLiquidityFilterConfig,
)
from src.trade_planning.option_strike_selection_result import (
    OptionStrikeSelectionRejection,
    OptionStrikeSelectionResult,
)


_UNSET = object()


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


def _entry(
    option_type,
    strike_price,
    last_traded_price=100.0,
    bid_price=_UNSET,
    ask_price=_UNSET,
    volume=10000,
    open_interest=50000,
    greeks=None,
):
    if bid_price is _UNSET:
        bid_price = last_traded_price - 1.0

    if ask_price is _UNSET:
        ask_price = last_traded_price + 1.0

    return OptionChainEntry(
        contract=_contract(option_type, strike_price),
        last_traded_price=last_traded_price,
        bid_price=bid_price,
        ask_price=ask_price,
        volume=volume,
        open_interest=open_interest,
        greeks=greeks,
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


def test_default_liquidity_config_preserves_closest_strike_behavior():
    ce_24200 = _entry(OptionType.CE, 24200, volume=0, open_interest=0)
    ce_24300 = _entry(OptionType.CE, 24300, volume=0, open_interest=0)

    selector = DynamicOptionStrikeSelector()
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24300, ce_24200), 24210.0),
    )

    assert result.has_selection is True
    assert result.selected_entry == ce_24200


def test_selector_rejects_low_volume():
    ce_24200 = _entry(OptionType.CE, 24200, volume=99)
    ce_24300 = _entry(OptionType.CE, 24300, volume=100)

    selector = DynamicOptionStrikeSelector(
        liquidity_config=OptionLiquidityFilterConfig(min_volume=100)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason
        == "CE strike 24200.0 rejected because volume below minimum 100"
        for rejection in result.rejected_entries
    )


def test_selector_rejects_low_open_interest():
    ce_24200 = _entry(OptionType.CE, 24200, open_interest=499)
    ce_24300 = _entry(OptionType.CE, 24300, open_interest=500)

    selector = DynamicOptionStrikeSelector(
        liquidity_config=OptionLiquidityFilterConfig(min_open_interest=500)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason
        == "CE strike 24200.0 rejected because open interest below minimum 500"
        for rejection in result.rejected_entries
    )


def test_selector_rejects_missing_bid_ask_when_required():
    ce_24200 = _entry(OptionType.CE, 24200, bid_price=None, ask_price=None)
    ce_24300 = _entry(OptionType.CE, 24300)

    selector = DynamicOptionStrikeSelector(
        liquidity_config=OptionLiquidityFilterConfig(require_bid_ask_quote=True)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason
        == "CE strike 24200.0 rejected because missing bid/ask quote"
        for rejection in result.rejected_entries
    )


def test_selector_rejects_wide_spread():
    ce_24200 = _entry(OptionType.CE, 24200, bid_price=98.0, ask_price=101.0)
    ce_24300 = _entry(OptionType.CE, 24300, bid_price=99.0, ask_price=100.0)

    selector = DynamicOptionStrikeSelector(
        liquidity_config=OptionLiquidityFilterConfig(max_spread=2.0)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason == "CE strike 24200.0 rejected because spread above maximum 2.0"
        for rejection in result.rejected_entries
    )


def test_selector_selects_farther_strike_when_closest_fails_liquidity():
    closest_ce = _entry(OptionType.CE, 24200, volume=10)
    farther_ce = _entry(OptionType.CE, 24300, volume=1000)

    selector = DynamicOptionStrikeSelector(
        liquidity_config=OptionLiquidityFilterConfig(min_volume=100)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((closest_ce, farther_ce), 24210.0),
    )

    assert result.has_selection is True
    assert result.selected_entry == farther_ce
    assert result.selected_reason == (
        "Selected CE strike closest to underlying price 24210.0"
    )


def test_selector_returns_no_selection_when_all_matching_strikes_fail_liquidity():
    ce_24200 = _entry(OptionType.CE, 24200, volume=10)
    ce_24300 = _entry(OptionType.CE, 24300, volume=20)
    pe_24200 = _entry(OptionType.PE, 24200, volume=1000)

    selector = DynamicOptionStrikeSelector(
        liquidity_config=OptionLiquidityFilterConfig(min_volume=100)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, pe_24200, ce_24300), 24210.0),
    )

    assert result.has_selection is False
    assert result.selected_entry is None
    assert result.selected_reason == (
        "No CE entries passed liquidity filters for long signal"
    )
    assert result.rejection_reasons == (
        "PE entry rejected because long signal requires CE",
        "CE strike 24200.0 rejected because volume below minimum 100",
        "CE strike 24300.0 rejected because volume below minimum 100",
    )


def test_option_liquidity_filter_config_validates_values():
    with pytest.raises(ValueError, match="min_volume cannot be negative"):
        OptionLiquidityFilterConfig(min_volume=-1)

    with pytest.raises(ValueError, match="min_open_interest cannot be negative"):
        OptionLiquidityFilterConfig(min_open_interest=-1)

    with pytest.raises(
        ValueError,
        match="max_spread must be greater than 0 when provided",
    ):
        OptionLiquidityFilterConfig(max_spread=0)


def test_default_greek_config_preserves_closest_strike_behavior():
    ce_24200 = _entry(OptionType.CE, 24200, greeks=None)
    ce_24300 = _entry(
        OptionType.CE,
        24300,
        greeks=OptionGreeks(delta=0.45, theta=-8.0, vega=12.0, gamma=0.04),
    )

    selector = DynamicOptionStrikeSelector()
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24300, ce_24200), 24210.0),
    )

    assert result.has_selection is True
    assert result.selected_entry == ce_24200


def test_selector_requires_greeks_when_configured():
    ce_24200 = _entry(OptionType.CE, 24200, greeks=None)
    ce_24300 = _entry(
        OptionType.CE,
        24300,
        greeks=OptionGreeks(delta=0.45, theta=-8.0, vega=12.0, gamma=0.04),
    )

    selector = DynamicOptionStrikeSelector(
        greek_config=OptionGreekFilterConfig(require_greeks=True)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason == "CE strike 24200.0 rejected because Greeks are missing"
        for rejection in result.rejected_entries
    )


def test_selector_rejects_weak_delta():
    ce_24200 = _entry(
        OptionType.CE,
        24200,
        greeks=OptionGreeks(delta=0.19, theta=-8.0, vega=12.0, gamma=0.04),
    )
    ce_24300 = _entry(
        OptionType.CE,
        24300,
        greeks=OptionGreeks(delta=0.25, theta=-8.0, vega=12.0, gamma=0.04),
    )

    selector = DynamicOptionStrikeSelector(
        greek_config=OptionGreekFilterConfig(min_abs_delta=0.2)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason
        == "CE strike 24200.0 rejected because absolute delta below minimum 0.2"
        for rejection in result.rejected_entries
    )


def test_selector_rejects_delta_above_maximum():
    ce_24200 = _entry(
        OptionType.CE,
        24200,
        greeks=OptionGreeks(delta=0.81, theta=-8.0, vega=12.0, gamma=0.04),
    )
    ce_24300 = _entry(
        OptionType.CE,
        24300,
        greeks=OptionGreeks(delta=0.65, theta=-8.0, vega=12.0, gamma=0.04),
    )

    selector = DynamicOptionStrikeSelector(
        greek_config=OptionGreekFilterConfig(max_abs_delta=0.8)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason
        == "CE strike 24200.0 rejected because absolute delta above maximum 0.8"
        for rejection in result.rejected_entries
    )


def test_selector_rejects_high_theta_risk_using_absolute_theta():
    ce_24200 = _entry(
        OptionType.CE,
        24200,
        greeks=OptionGreeks(delta=0.45, theta=-12.0, vega=12.0, gamma=0.04),
    )
    ce_24300 = _entry(
        OptionType.CE,
        24300,
        greeks=OptionGreeks(delta=0.45, theta=-8.0, vega=12.0, gamma=0.04),
    )

    selector = DynamicOptionStrikeSelector(
        greek_config=OptionGreekFilterConfig(max_abs_theta=10.0)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason
        == "CE strike 24200.0 rejected because absolute theta above maximum 10.0"
        for rejection in result.rejected_entries
    )


def test_selector_rejects_high_vega():
    ce_24200 = _entry(
        OptionType.CE,
        24200,
        greeks=OptionGreeks(delta=0.45, theta=-8.0, vega=21.0, gamma=0.04),
    )
    ce_24300 = _entry(
        OptionType.CE,
        24300,
        greeks=OptionGreeks(delta=0.45, theta=-8.0, vega=19.0, gamma=0.04),
    )

    selector = DynamicOptionStrikeSelector(
        greek_config=OptionGreekFilterConfig(max_vega=20.0)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason == "CE strike 24200.0 rejected because vega above maximum 20.0"
        for rejection in result.rejected_entries
    )


def test_selector_rejects_high_gamma():
    ce_24200 = _entry(
        OptionType.CE,
        24200,
        greeks=OptionGreeks(delta=0.45, theta=-8.0, vega=12.0, gamma=0.07),
    )
    ce_24300 = _entry(
        OptionType.CE,
        24300,
        greeks=OptionGreeks(delta=0.45, theta=-8.0, vega=12.0, gamma=0.04),
    )

    selector = DynamicOptionStrikeSelector(
        greek_config=OptionGreekFilterConfig(max_gamma=0.05)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, ce_24300), 24210.0),
    )

    assert result.selected_entry == ce_24300
    assert any(
        rejection.entry == ce_24200
        and rejection.reason == "CE strike 24200.0 rejected because gamma above maximum 0.05"
        for rejection in result.rejected_entries
    )


def test_selector_selects_farther_strike_when_closest_fails_greeks():
    closest_ce = _entry(
        OptionType.CE,
        24200,
        greeks=OptionGreeks(delta=0.1, theta=-8.0, vega=12.0, gamma=0.04),
    )
    farther_ce = _entry(
        OptionType.CE,
        24300,
        greeks=OptionGreeks(delta=0.35, theta=-8.0, vega=12.0, gamma=0.04),
    )

    selector = DynamicOptionStrikeSelector(
        greek_config=OptionGreekFilterConfig(min_abs_delta=0.2)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((closest_ce, farther_ce), 24210.0),
    )

    assert result.has_selection is True
    assert result.selected_entry == farther_ce
    assert result.selected_reason == (
        "Selected CE strike closest to underlying price 24210.0"
    )


def test_selector_returns_no_selection_when_all_matching_strikes_fail_greeks():
    ce_24200 = _entry(
        OptionType.CE,
        24200,
        greeks=OptionGreeks(delta=0.1, theta=-8.0, vega=12.0, gamma=0.04),
    )
    ce_24300 = _entry(
        OptionType.CE,
        24300,
        greeks=OptionGreeks(delta=0.15, theta=-8.0, vega=12.0, gamma=0.04),
    )
    pe_24200 = _entry(
        OptionType.PE,
        24200,
        greeks=OptionGreeks(delta=-0.35, theta=-8.0, vega=12.0, gamma=0.04),
    )

    selector = DynamicOptionStrikeSelector(
        greek_config=OptionGreekFilterConfig(min_abs_delta=0.2)
    )
    result = selector.select(
        signal=_signal(SignalType.LONG),
        snapshot=_snapshot((ce_24200, pe_24200, ce_24300), 24210.0),
    )

    assert result.has_selection is False
    assert result.selected_entry is None
    assert result.selected_reason == (
        "No CE entries passed Greek filters for long signal"
    )
    assert result.rejection_reasons == (
        "PE entry rejected because long signal requires CE",
        "CE strike 24200.0 rejected because absolute delta below minimum 0.2",
        "CE strike 24300.0 rejected because absolute delta below minimum 0.2",
    )


def test_option_greek_filter_config_validates_values():
    with pytest.raises(
        ValueError,
        match="min_abs_delta must be greater than 0 and <= 1",
    ):
        OptionGreekFilterConfig(min_abs_delta=0)

    with pytest.raises(
        ValueError,
        match="max_abs_delta must be greater than 0 and <= 1",
    ):
        OptionGreekFilterConfig(max_abs_delta=1.1)

    with pytest.raises(
        ValueError,
        match="min_abs_delta cannot be greater than max_abs_delta",
    ):
        OptionGreekFilterConfig(min_abs_delta=0.8, max_abs_delta=0.7)

    with pytest.raises(
        ValueError,
        match="max_abs_theta must be greater than 0 when provided",
    ):
        OptionGreekFilterConfig(max_abs_theta=0)

    with pytest.raises(
        ValueError,
        match="max_vega must be greater than 0 when provided",
    ):
        OptionGreekFilterConfig(max_vega=0)

    with pytest.raises(
        ValueError,
        match="max_gamma must be greater than 0 when provided",
    ):
        OptionGreekFilterConfig(max_gamma=0)


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
