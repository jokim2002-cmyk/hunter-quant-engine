"""
Base Backtest Pipeline Contract

Defines the abstract contract for complete backtest pipelines.
"""

from abc import ABC, abstractmethod

from src.backtesting.backtest_result import BacktestResult


class BaseBacktestPipeline(ABC):
    """
    Base contract for backtest pipelines.

    Backtest pipelines orchestrate strategy, trade planning, risk management,
    and trade execution over historical market data.

    Backtest pipelines do not:
    - detect market events directly
    - calculate price fills
    - calculate performance summaries directly
    - mutate historical data
    """

    @abstractmethod
    def run(self) -> BacktestResult:
        """
        Run the complete backtest pipeline.

        Returns:
            Immutable completed backtest result.
        """
        raise NotImplementedError
