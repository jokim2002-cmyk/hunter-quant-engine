"""
Option Buy Backtest Summary

Aggregates supplied-data option-buy backtest results.
"""

from dataclasses import dataclass

from src.backtesting.option_premium_backtest_result import OptionPremiumBacktestResult


@dataclass(frozen=True)
class OptionBuyBacktestSummary:
    """
    Summary for a multi-signal option-buy backtest run.
    """

    planned_signals: int
    rejected_plans: int
    failed_backtests: int = 0
    results: tuple[OptionPremiumBacktestResult, ...] = ()
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self):
        """
        Validate and normalize summary fields.
        """
        if self.planned_signals < 0:
            raise ValueError("planned_signals must be greater than or equal to 0")

        if self.rejected_plans < 0:
            raise ValueError("rejected_plans must be greater than or equal to 0")

        if self.failed_backtests < 0:
            raise ValueError("failed_backtests must be greater than or equal to 0")

        object.__setattr__(self, "results", tuple(self.results))
        object.__setattr__(self, "rejection_reasons", tuple(self.rejection_reasons))

    @property
    def completed_trades(self) -> int:
        """
        Return completed backtested trades.
        """
        return len(self.results)

    @property
    def has_results(self) -> bool:
        """
        Return True when at least one backtest result exists.
        """
        return self.completed_trades > 0

    @property
    def winning_trades(self) -> int:
        """
        Return count of positive net PnL results.
        """
        return sum(1 for result in self.results if result.is_win)

    @property
    def losing_trades(self) -> int:
        """
        Return count of negative net PnL results.
        """
        return sum(1 for result in self.results if result.is_loss)

    @property
    def breakeven_trades(self) -> int:
        """
        Return count of zero net PnL results.
        """
        return self.completed_trades - self.winning_trades - self.losing_trades

    @property
    def win_rate(self) -> float:
        """
        Return winning trades divided by completed trades.
        """
        if self.completed_trades == 0:
            return 0.0

        return self.winning_trades / self.completed_trades

    @property
    def total_gross_pnl(self) -> float:
        """
        Return total gross PnL across completed results.
        """
        return sum(result.gross_pnl for result in self.results)

    @property
    def total_net_pnl(self) -> float:
        """
        Return total net PnL across completed results.
        """
        return sum(result.net_pnl for result in self.results)

    @property
    def total_estimated_charges(self) -> float:
        """
        Return total estimated charges across completed results.
        """
        return sum(result.estimated_charges for result in self.results)
