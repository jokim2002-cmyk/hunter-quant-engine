from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal


def test_trade_signal_can_be_created():
    created_at = datetime(2026, 1, 1)

    signal = TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.85,
        rationale=(
            "Bullish BOS",
            "Bullish Order Block",
            "Liquidity Sweep",
        ),
        created_at=created_at,
    )

    assert signal.signal_type == SignalType.LONG
    assert signal.strength == SignalStrength.STRONG
    assert signal.confidence == 0.85
    assert signal.rationale == (
        "Bullish BOS",
        "Bullish Order Block",
        "Liquidity Sweep",
    )
    assert signal.created_at == created_at


def test_trade_signal_is_immutable():
    signal = TradeSignal(
        signal_type=SignalType.SHORT,
        strength=SignalStrength.MEDIUM,
        confidence=0.65,
        rationale=("Bearish CHOCH",),
        created_at=datetime(2026, 1, 1),
    )

    with pytest.raises(FrozenInstanceError):
        signal.confidence = 0.90
