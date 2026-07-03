"""
Backtest Result Model

Represents an immutable completed backtest result.
"""

from dataclasses import dataclass

from src.backtesting.performance_summary import PerformanceSummary
from src.backtesting.trade_result import TradeResult


@dataclass(frozen=True)
class BacktestResult:
    """
    Immutable completed backtest result.
    """

    trades: tuple[TradeResult, ...]
    performance_summary: PerformanceSummary

    def __post_init__(self):
        if self.performance_summary.total_trades != len(self.trades):
            raise ValueError(
                "performance_summary.total_trades must match number of trades."
            )
