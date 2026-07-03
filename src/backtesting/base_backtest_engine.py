"""
Base Backtest Engine Contract

Defines the abstract contract for all backtesting engines.
"""

from abc import ABC, abstractmethod

from src.backtesting.backtest_result import BacktestResult


class BaseBacktestEngine(ABC):
    """
    Base contract for all backtesting engines.

    Backtest engines orchestrate strategy and risk components over
    historical market data.

    Backtest engines do not:
    - detect market events directly
    - create strategy logic
    - calculate risk directly
    - execute live trades
    """

    @abstractmethod
    def run(self) -> BacktestResult:
        """
        Run a backtest.

        Returns:
            Immutable backtest result.
        """
        raise NotImplementedError
