"""
Trade Candidate Model

Represents executable trade candidate levels created from a strategy signal.
"""

from dataclasses import dataclass

from src.strategy.trade_signal import TradeSignal


@dataclass(frozen=True)
class TradeCandidate:
    """
    Immutable executable trade candidate.

    Trade candidates bridge strategy signals and risk planning.
    """

    signal: TradeSignal
    entry_price: float
    stop_loss: float
