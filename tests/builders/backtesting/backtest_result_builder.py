"""
Backtest Result Builder

Test builder for creating BacktestResult objects.
"""

from src.backtesting.backtest_result import BacktestResult
from src.backtesting.performance_summary import PerformanceSummary
from src.backtesting.trade_result import TradeResult
from tests.builders.backtesting.performance_summary_builder import (
    PerformanceSummaryBuilder,
)


class BacktestResultBuilder:
    """
    Builder for BacktestResult test objects.
    """

    def __init__(self):
        self._trades: tuple[TradeResult, ...] = ()
        self._performance_summary = PerformanceSummaryBuilder().build()

    def with_trades(self, *trades: TradeResult):
        self._trades = trades
        return self

    def with_performance_summary(self, performance_summary: PerformanceSummary):
        self._performance_summary = performance_summary
        return self

    def build(self) -> BacktestResult:
        return BacktestResult(
            trades=self._trades,
            performance_summary=self._performance_summary,
        )
