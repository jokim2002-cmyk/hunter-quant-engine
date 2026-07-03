"""
Backtest Result Model

Represents an immutable backtest result.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestResult:
    total_trades: int
