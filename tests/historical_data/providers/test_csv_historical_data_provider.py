"""
CSV Historical Data Provider Tests
"""

from datetime import datetime

from src.historical_data.providers.csv_historical_data_provider import (
    CSVHistoricalDataProvider,
)


def test_load_returns_all_candles():
    """
    Should load every candle from the CSV file.
    """
    provider = CSVHistoricalDataProvider(
        "tests/historical_data/data/sample_candles.csv",
    )

    candles = provider.load()

    assert len(candles) == 2


def test_load_creates_expected_candle_values():
    """
    Should correctly map CSV values to Candle objects.
    """
    provider = CSVHistoricalDataProvider(
        "tests/historical_data/data/sample_candles.csv",
    )

    candle = provider.load()[0]

    assert candle.datetime == datetime(2024, 1, 1)
    assert candle.open == 100.0
    assert candle.high == 105.0
    assert candle.low == 99.0
    assert candle.close == 104.0
    assert candle.volume == 1000.0
