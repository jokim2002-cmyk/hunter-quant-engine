"""
Trade Signal

Represents an immutable strategy signal.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType


@dataclass(frozen=True)
class TradeSignal:
    signal_type: SignalType
    strength: SignalStrength
    confidence: float
    rationale: Tuple[str, ...]
    created_at: datetime
