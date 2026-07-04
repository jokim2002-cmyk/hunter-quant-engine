"""
Trade Candidate Builder

Test builder for creating TradeCandidate objects.
"""

from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.trade_candidate import TradeCandidate
from tests.builders.common.defaults import DEFAULT_TIMESTAMP


class TradeCandidateBuilder:
    """
    Builder for TradeCandidate test objects.
    """

    def __init__(self):
        self._signal = TradeSignal(
            signal_type=SignalType.LONG,
            strength=SignalStrength.MEDIUM,
            confidence=0.75,
            rationale=("Test signal.",),
            created_at=DEFAULT_TIMESTAMP,
        )
        self._entry_price = 100.0
        self._stop_loss = 95.0

    def with_signal(self, signal: TradeSignal):
        self._signal = signal
        return self

    def with_entry_price(self, entry_price: float):
        self._entry_price = entry_price
        return self

    def with_stop_loss(self, stop_loss: float):
        self._stop_loss = stop_loss
        return self

    def build(self):
        return TradeCandidate(
            signal=self._signal,
            entry_price=self._entry_price,
            stop_loss=self._stop_loss,
        )
