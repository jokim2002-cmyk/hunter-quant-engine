"""
In-Memory Historical Data Provider Tests
"""

from datetime import datetime

from src.historical_data.providers.in_memory_historical_data_provider import (
    InMemoryHistoricalDataProvider,
)
from src.models.candle import Candle


def test_load_returns_same_candle_collection():
    """
    Should return the same immutable candle collection provided at construction.
    """
    candles = (
        Candle(
            datetime=datetime(2024, 1, 1),
            open=100.0,
            high=105.0,
            low=99.0,
            close=104.0,
            volume=1000.0,
        ),
        Candle(
            datetime=datetime(2024, 1, 2),
            open=104.0,
            high=108.0,
            low=103.0,
            close=107.0,
            volume=1200.0,
        ),
    )

    provider = InMemoryHistoricalDataProvider(candles)

    loaded = provider.load()

    assert loaded is candles


def test_load_returns_empty_tuple_when_initialized_empty():
    """
    Should return an empty tuple when initialized with no candles.
    """
    provider = InMemoryHistoricalDataProvider(())

    assert provider.load() == ()
