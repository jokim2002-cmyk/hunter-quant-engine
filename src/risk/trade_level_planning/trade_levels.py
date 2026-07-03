"""
Trade Levels Model

Represents immutable planned trade price levels.
"""

from dataclasses import dataclass

from src.strategy.signal_type import SignalType


@dataclass(frozen=True)
class TradeLevels:
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float

    def __post_init__(self):
        if self.signal_type == SignalType.NEUTRAL:
            raise ValueError("TradeLevels cannot be created for neutral signals.")

        if self.entry_price <= 0:
            raise ValueError("entry_price must be greater than zero.")

        if self.stop_loss <= 0:
            raise ValueError("stop_loss must be greater than zero.")

        if self.take_profit <= 0:
            raise ValueError("take_profit must be greater than zero.")

        if self.signal_type == SignalType.LONG:
            self._validate_long_levels()

        if self.signal_type == SignalType.SHORT:
            self._validate_short_levels()

    def _validate_long_levels(self):
        if self.stop_loss >= self.entry_price:
            raise ValueError("Long trade stop_loss must be below entry_price.")

        if self.take_profit <= self.entry_price:
            raise ValueError("Long trade take_profit must be above entry_price.")

    def _validate_short_levels(self):
        if self.stop_loss <= self.entry_price:
            raise ValueError("Short trade stop_loss must be above entry_price.")

        if self.take_profit >= self.entry_price:
            raise ValueError("Short trade take_profit must be below entry_price.")
