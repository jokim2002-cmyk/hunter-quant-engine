"""
Base Historical Data Provider Contract

Defines the abstract contract for loading historical market data.
"""

from abc import ABC, abstractmethod

from src.models.candle import Candle


class BaseHistoricalDataProvider(ABC):
    """
    Base contract for all historical data providers.

    Historical data providers load immutable candle data from a source.

    Historical data providers do not:
    - detect market events
    - create strategy signals
    - calculate risk
    - execute backtests
    """

    @abstractmethod
    def load(self) -> tuple[Candle, ...]:
        """
        Load historical candle data.

        Returns:
            Tuple of immutable candles.
            Returns an empty tuple when no candles are available.
        """
        raise NotImplementedError
