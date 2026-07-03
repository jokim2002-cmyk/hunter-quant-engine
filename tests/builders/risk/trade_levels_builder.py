"""
Trade Levels Builder

Test builder for creating TradeLevels objects.
"""

from src.risk.trade_level_planning.trade_levels import TradeLevels
from src.strategy.signal_type import SignalType


class TradeLevelsBuilder:
    """
    Builder for TradeLevels test objects.
    """

    def __init__(self):
        self._signal_type = SignalType.LONG
        self._entry_price = 100.0
        self._stop_loss = 95.0
        self._take_profit = 110.0

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

    def build(self):
        return TradeLevels(
            signal_type=self._signal_type,
            entry_price=self._entry_price,
            stop_loss=self._stop_loss,
            take_profit=self._take_profit,
        )
