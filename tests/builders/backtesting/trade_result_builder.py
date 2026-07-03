"""
Trade Result Builder

Test builder for creating TradeResult objects.
"""

from datetime import datetime

from src.backtesting.trade_result import TradeResult
from src.strategy.signal_type import SignalType


class TradeResultBuilder:
    """
    Builder for TradeResult test objects.
    """

    def __init__(self):
        self._signal_type = SignalType.LONG
        self._entry_price = 100.0
        self._exit_price = 110.0
        self._stop_loss = 95.0
        self._take_profit = 110.0
        self._position_size = 20.0
        self._pnl = 200.0
        self._risk_multiple = 2.0
        self._opened_at = datetime(2026, 1, 1, 10, 0)
        self._closed_at = datetime(2026, 1, 1, 11, 0)

    def with_signal_type(self, signal_type: SignalType):
        self._signal_type = signal_type
        return self

    def with_entry_price(self, entry_price: float):
        self._entry_price = entry_price
        return self

    def with_exit_price(self, exit_price: float):
        self._exit_price = exit_price
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

    def with_pnl(self, pnl: float):
        self._pnl = pnl
        return self

    def with_risk_multiple(self, risk_multiple: float):
        self._risk_multiple = risk_multiple
        return self

    def with_opened_at(self, opened_at: datetime):
        self._opened_at = opened_at
        return self

    def with_closed_at(self, closed_at: datetime):
        self._closed_at = closed_at
        return self

    def build(self) -> TradeResult:
        return TradeResult(
            signal_type=self._signal_type,
            entry_price=self._entry_price,
            exit_price=self._exit_price,
            stop_loss=self._stop_loss,
            take_profit=self._take_profit,
            position_size=self._position_size,
            pnl=self._pnl,
            risk_multiple=self._risk_multiple,
            opened_at=self._opened_at,
            closed_at=self._closed_at,
        )
