"""
Performance Summary Model

Represents immutable aggregate backtest performance metrics.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceSummary:
    """
    Immutable aggregate performance summary.
    """

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_pnl: float
    max_drawdown: float

    def __post_init__(self):
        if self.total_trades < 0:
            raise ValueError("total_trades cannot be negative.")

        if self.winning_trades < 0:
            raise ValueError("winning_trades cannot be negative.")

        if self.losing_trades < 0:
            raise ValueError("losing_trades cannot be negative.")

        if self.winning_trades + self.losing_trades > self.total_trades:
            raise ValueError(
                "winning_trades and losing_trades cannot exceed total_trades."
            )

        if self.win_rate < 0:
            raise ValueError("win_rate cannot be negative.")

        if self.win_rate > 1:
            raise ValueError("win_rate cannot be greater than 1.")

        if self.max_drawdown < 0:
            raise ValueError("max_drawdown cannot be negative.")
