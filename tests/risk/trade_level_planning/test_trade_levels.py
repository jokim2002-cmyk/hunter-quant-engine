"""
Tests for TradeLevels.
"""

from dataclasses import FrozenInstanceError

import pytest

from src.risk.trade_level_planning.trade_levels import TradeLevels
from src.strategy.signal_type import SignalType


def test_long_trade_levels_can_be_created():
    levels = TradeLevels(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
    )

    assert levels.signal_type == SignalType.LONG
    assert levels.entry_price == 100.0
    assert levels.stop_loss == 95.0
    assert levels.take_profit == 110.0


def test_short_trade_levels_can_be_created():
    levels = TradeLevels(
        signal_type=SignalType.SHORT,
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
    )

    assert levels.signal_type == SignalType.SHORT
    assert levels.entry_price == 100.0
    assert levels.stop_loss == 105.0
    assert levels.take_profit == 90.0


def test_trade_levels_are_immutable():
    levels = TradeLevels(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
    )

    with pytest.raises(FrozenInstanceError):
        levels.entry_price = 101.0


def test_raises_error_for_neutral_signal():
    with pytest.raises(
        ValueError,
        match="TradeLevels cannot be created for neutral signals.",
    ):
        TradeLevels(
            signal_type=SignalType.NEUTRAL,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "entry_price",
        "stop_loss",
        "take_profit",
    ],
)
def test_raises_error_when_numeric_field_is_zero(field_name):
    values = {
        "signal_type": SignalType.LONG,
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
    }
    values[field_name] = 0.0

    with pytest.raises(ValueError, match=f"{field_name} must be greater than zero."):
        TradeLevels(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "entry_price",
        "stop_loss",
        "take_profit",
    ],
)
def test_raises_error_when_numeric_field_is_negative(field_name):
    values = {
        "signal_type": SignalType.LONG,
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
    }
    values[field_name] = -1.0

    with pytest.raises(ValueError, match=f"{field_name} must be greater than zero."):
        TradeLevels(**values)


def test_raises_error_when_long_stop_loss_is_not_below_entry_price():
    with pytest.raises(
        ValueError,
        match="Long trade stop_loss must be below entry_price.",
    ):
        TradeLevels(
            signal_type=SignalType.LONG,
            entry_price=100.0,
            stop_loss=100.0,
            take_profit=110.0,
        )


def test_raises_error_when_long_take_profit_is_not_above_entry_price():
    with pytest.raises(
        ValueError,
        match="Long trade take_profit must be above entry_price.",
    ):
        TradeLevels(
            signal_type=SignalType.LONG,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=100.0,
        )


def test_raises_error_when_short_stop_loss_is_not_above_entry_price():
    with pytest.raises(
        ValueError,
        match="Short trade stop_loss must be above entry_price.",
    ):
        TradeLevels(
            signal_type=SignalType.SHORT,
            entry_price=100.0,
            stop_loss=100.0,
            take_profit=90.0,
        )


def test_raises_error_when_short_take_profit_is_not_below_entry_price():
    with pytest.raises(
        ValueError,
        match="Short trade take_profit must be below entry_price.",
    ):
        TradeLevels(
            signal_type=SignalType.SHORT,
            entry_price=100.0,
            stop_loss=105.0,
            take_profit=100.0,
        )
