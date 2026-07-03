"""
Tests for TradeSignalBuilder.
"""

from datetime import datetime

from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from tests.builders.strategy.trade_signal_builder import TradeSignalBuilder


def test_builds_long_trade_signal_by_default():
    signal = TradeSignalBuilder().build()

    assert signal.signal_type == SignalType.LONG
    assert signal.strength == SignalStrength.MEDIUM
    assert signal.confidence == 0.75
    assert signal.rationale == ("Test signal.",)


def test_builds_short_trade_signal():
    signal = TradeSignalBuilder().short().build()

    assert signal.signal_type == SignalType.SHORT
    assert signal.strength == SignalStrength.MEDIUM
    assert signal.confidence == 0.75


def test_builds_neutral_trade_signal():
    signal = TradeSignalBuilder().neutral().build()

    assert signal.signal_type == SignalType.NEUTRAL
    assert signal.strength == SignalStrength.WEAK
    assert signal.confidence == 0.0


def test_builds_trade_signal_with_custom_strength():
    signal = TradeSignalBuilder().with_strength(SignalStrength.STRONG).build()

    assert signal.strength == SignalStrength.STRONG


def test_builds_trade_signal_with_custom_confidence():
    signal = TradeSignalBuilder().with_confidence(0.9).build()

    assert signal.confidence == 0.9


def test_builds_trade_signal_with_custom_rationale():
    signal = (
        TradeSignalBuilder()
        .with_rationale("Reason one.", "Reason two.")
        .build()
    )

    assert signal.rationale == ("Reason one.", "Reason two.")


def test_builds_trade_signal_with_custom_created_at():
    created_at = datetime(2026, 6, 1)

    signal = TradeSignalBuilder().created_at(created_at).build()

    assert signal.created_at == created_at
