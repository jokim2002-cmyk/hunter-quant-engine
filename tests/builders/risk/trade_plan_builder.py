"""
Trade Plan Builder

Test builder for creating TradePlan objects.
"""

from datetime import datetime

from src.risk.trade_plan import TradePlan
from src.strategy.signal_type import SignalType


class TradePlanBuilder:
    """
    Builder for TradePlan test objects.
    """

    def __init__(self):
        self._signal_type = SignalType.LONG
        self._entry_price = 100.0
        self._stop_loss = 95.0
        self._take_profit = 110.0
        self._position_size = 20.0
        self._risk_amount = 100.0
        self._reward_amount = 200.0
        self._created_at = datetime(2026, 4, 1)

    def long(self):
        self._signal_type = SignalType.LONG
        self._entry_price = 100.0
        self._stop_loss = 95.0
        self._take_profit = 110.0
        return self

    def short(self):
        self._signal_type = SignalType.SHORT
        self._entry_price = 100.0
        self._stop_loss = 105.0
        self._take_profit = 90.0
        return self

    def with_entry_price(self, entry_price: float):
        self._entry_price = entry_price
        return self

    def with_stop_loss(self, stop_loss: float):
        self._stop_loss = stop_loss
        return self

    def with_take_profit(self, take_profit: float):
        self._take_profit = take_profit
        return self

    def with_position_size(self, position_size: float):
        self._position_size = position_size
        return self

    def with_risk_amount(self, risk_amount: float):
        self._risk_amount = risk_amount
        return self

    def with_reward_amount(self, reward_amount: float):
        self._reward_amount = reward_amount
        return self

    def created_at(self, created_at: datetime):
        self._created_at = created_at
        return self

    def build(self):
        return TradePlan(
            signal_type=self._signal_type,
            entry_price=self._entry_price,
            stop_loss=self._stop_loss,
            take_profit=self._take_profit,
            position_size=self._position_size,
            risk_amount=self._risk_amount,
            reward_amount=self._reward_amount,
            created_at=self._created_at,
        )
