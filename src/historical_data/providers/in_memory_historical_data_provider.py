"""
In-Memory Historical Data Provider

Loads historical candle data from memory.
"""

from src.historical_data.providers.base_historical_data_provider import (
    BaseHistoricalDataProvider,
)
from src.models.candle import Candle


class InMemoryHistoricalDataProvider(BaseHistoricalDataProvider):
    """
    Historical data provider backed by an immutable in-memory candle collection.
    """

    def __init__(
        self,
        candles: tuple[Candle, ...],
    ):
        """
        Initialize the provider.

        Args:
            candles: Immutable historical candle collection.
        """
        self._candles = candles

    def load(self) -> tuple[Candle, ...]:
        """
        Load historical candle data.

        Returns:
            Immutable historical candle collection.
        """
        return self._candles
