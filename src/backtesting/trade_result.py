"""
Trade Result Model

Represents an immutable completed historical trade.
"""

from dataclasses import dataclass
from datetime import datetime

from src.strategy.signal_type import SignalType


@dataclass(frozen=True)
class TradeResult:
    """
    Immutable historical trade result.
    """

    signal_type: SignalType

    entry_price: float
    exit_price: float

    stop_loss: float
    take_profit: float

    position_size: float

    pnl: float
    risk_multiple: float

    opened_at: datetime
    closed_at: datetime
