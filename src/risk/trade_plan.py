"""
Trade Plan Model

Represents an immutable risk-approved trade plan.
"""

from dataclasses import dataclass
from datetime import datetime

from src.strategy.signal_type import SignalType


@dataclass(frozen=True)
class TradePlan:
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    risk_amount: float
    reward_amount: float
    created_at: datetime

    def __post_init__(self):
        if self.signal_type == SignalType.NEUTRAL:
            raise ValueError("TradePlan cannot be created for neutral signals.")

        if self.entry_price <= 0:
            raise ValueError("entry_price must be greater than zero.")

        if self.stop_loss <= 0:
            raise ValueError("stop_loss must be greater than zero.")

        if self.take_profit <= 0:
            raise ValueError("take_profit must be greater than zero.")

        if self.position_size <= 0:
            raise ValueError("position_size must be greater than zero.")

        if self.risk_amount <= 0:
            raise ValueError("risk_amount must be greater than zero.")

        if self.reward_amount <= 0:
            raise ValueError("reward_amount must be greater than zero.")

        if self.signal_type == SignalType.LONG:
            self._validate_long_prices()

        if self.signal_type == SignalType.SHORT:
            self._validate_short_prices()

    def _validate_long_prices(self):
        if self.stop_loss >= self.entry_price:
            raise ValueError("Long trade stop_loss must be below entry_price.")

        if self.take_profit <= self.entry_price:
            raise ValueError("Long trade take_profit must be above entry_price.")

    def _validate_short_prices(self):
        if self.stop_loss <= self.entry_price:
            raise ValueError("Short trade stop_loss must be above entry_price.")

        if self.take_profit >= self.entry_price:
            raise ValueError("Short trade take_profit must be below entry_price.")
