"""
Performance Summary Builder

Test builder for creating PerformanceSummary objects.
"""

from src.backtesting.performance_summary import PerformanceSummary


class PerformanceSummaryBuilder:
    """
    Builder for PerformanceSummary test objects.
    """

    def __init__(self):
        self._total_trades = 0
        self._winning_trades = 0
        self._losing_trades = 0
        self._win_rate = 0.0
        self._total_pnl = 0.0
        self._average_pnl = 0.0
        self._max_drawdown = 0.0

    def with_total_trades(self, total_trades: int):
        self._total_trades = total_trades
        return self

    def with_winning_trades(self, winning_trades: int):
        self._winning_trades = winning_trades
        return self

    def with_losing_trades(self, losing_trades: int):
        self._losing_trades = losing_trades
        return self

    def with_win_rate(self, win_rate: float):
        self._win_rate = win_rate
        return self

    def with_total_pnl(self, total_pnl: float):
        self._total_pnl = total_pnl
        return self

    def with_average_pnl(self, average_pnl: float):
        self._average_pnl = average_pnl
        return self

    def with_max_drawdown(self, max_drawdown: float):
        self._max_drawdown = max_drawdown
        return self

    def build(self) -> PerformanceSummary:
        return PerformanceSummary(
            total_trades=self._total_trades,
            winning_trades=self._winning_trades,
            losing_trades=self._losing_trades,
            win_rate=self._win_rate,
            total_pnl=self._total_pnl,
            average_pnl=self._average_pnl,
            max_drawdown=self._max_drawdown,
        )
