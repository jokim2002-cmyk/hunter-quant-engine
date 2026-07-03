"""
Tests for TradeLevelsBuilder.
"""

from src.strategy.signal_type import SignalType
from tests.builders.risk.trade_levels_builder import TradeLevelsBuilder


def test_builds_long_trade_levels_by_default():
    levels = TradeLevelsBuilder().build()

    assert levels.signal_type == SignalType.LONG
    assert levels.entry_price == 100.0
    assert levels.stop_loss == 95.0
    assert levels.take_profit == 110.0


def test_builds_short_trade_levels():
    levels = TradeLevelsBuilder().short().build()

    assert levels.signal_type == SignalType.SHORT
    assert levels.entry_price == 100.0
    assert levels.stop_loss == 105.0
    assert levels.take_profit == 90.0


def test_builds_trade_levels_with_custom_prices():
    levels = (
        TradeLevelsBuilder()
        .with_entry_price(200.0)
        .with_stop_loss(190.0)
        .with_take_profit(220.0)
        .build()
    )

    assert levels.entry_price == 200.0
    assert levels.stop_loss == 190.0
    assert levels.take_profit == 220.0
