"""
Trade Signal Builder

Test builder for creating TradeSignal objects.
"""

from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from tests.builders.common.defaults import DEFAULT_TIMESTAMP


class TradeSignalBuilder:
    """
    Builder for TradeSignal test objects.
    """

    def __init__(self):
        self._signal_type = SignalType.LONG
        self._strength = SignalStrength.MEDIUM
        self._confidence = 0.75
        self._rationale = ("Test signal.",)
        self._created_at = DEFAULT_TIMESTAMP

    def long(self):
        self._signal_type = SignalType.LONG
        self._strength = SignalStrength.MEDIUM
        self._confidence = 0.75
        return self

    def short(self):
        self._signal_type = SignalType.SHORT
        self._strength = SignalStrength.MEDIUM
        self._confidence = 0.75
        return self

    def neutral(self):
        self._signal_type = SignalType.NEUTRAL
        self._strength = SignalStrength.WEAK
        self._confidence = 0.0
        return self

    def with_strength(self, strength: SignalStrength):
        self._strength = strength
        return self

    def with_confidence(self, confidence: float):
        self._confidence = confidence
        return self

    def with_rationale(self, *rationale: str):
        self._rationale = rationale
        return self

    def created_at(self, created_at):
        self._created_at = created_at
        return self

    def build(self):
        return TradeSignal(
            signal_type=self._signal_type,
            strength=self._strength,
            confidence=self._confidence,
            rationale=self._rationale,
            created_at=self._created_at,
        )
