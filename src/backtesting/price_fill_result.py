"""
Price Fill Result Model

Represents an immutable price fill outcome for one candle.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PriceFillResult:
    filled: bool
    fill_price: float | None
    reason: str | None
