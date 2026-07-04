"""
Trade Candidate Builder Tests
"""

from src.trade_planning.trade_candidate import TradeCandidate
from tests.builders.strategy.trade_signal_builder import TradeSignalBuilder
from tests.builders.trade_planning.trade_candidate_builder import (
    TradeCandidateBuilder,
)


def test_trade_candidate_builder_builds_trade_candidate():
    candidate = TradeCandidateBuilder().build()

    assert isinstance(candidate, TradeCandidate)


def test_trade_candidate_builder_sets_signal():
    signal = TradeSignalBuilder().short().build()

    candidate = TradeCandidateBuilder().with_signal(signal).build()

    assert candidate.signal is signal


def test_trade_candidate_builder_sets_entry_and_stop_loss():
    candidate = (
        TradeCandidateBuilder()
        .with_entry_price(150.0)
        .with_stop_loss(145.0)
        .build()
    )

    assert candidate.entry_price == 150.0
    assert candidate.stop_loss == 145.0
