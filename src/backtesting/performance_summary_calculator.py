"""
Performance Summary Calculator

Calculates aggregate performance metrics from completed trade results.
"""

from src.backtesting.performance_summary import PerformanceSummary
from src.backtesting.trade_result import TradeResult


class PerformanceSummaryCalculator:
    """
    Calculates immutable performance summaries from trade results.
    """

    def calculate(self, trades: tuple[TradeResult, ...]) -> PerformanceSummary:
        """
        Calculate aggregate performance metrics.

        Args:
            trades: Completed historical trades.

        Returns:
            Immutable performance summary.
        """
        total_trades = len(trades)

        if total_trades == 0:
            return PerformanceSummary(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                average_pnl=0.0,
                max_drawdown=0.0,
            )

        winning_trades = sum(1 for trade in trades if trade.pnl > 0)
        losing_trades = sum(1 for trade in trades if trade.pnl < 0)
        total_pnl = sum(trade.pnl for trade in trades)
        average_pnl = total_pnl / total_trades
        win_rate = winning_trades / total_trades
        max_drawdown = self._calculate_max_drawdown(trades)

        return PerformanceSummary(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            average_pnl=average_pnl,
            max_drawdown=max_drawdown,
        )

    def _calculate_max_drawdown(self, trades: tuple[TradeResult, ...]) -> float:
        equity = 0.0
        peak_equity = 0.0
        max_drawdown = 0.0

        for trade in trades:
            equity += trade.pnl
            peak_equity = max(peak_equity, equity)
            drawdown = peak_equity - equity
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown
