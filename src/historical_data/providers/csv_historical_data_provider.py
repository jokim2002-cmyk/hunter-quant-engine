"""
CSV Historical Data Provider

Loads historical candle data from a CSV file.
"""

import csv
from datetime import datetime
from pathlib import Path

from src.historical_data.providers.base_historical_data_provider import (
    BaseHistoricalDataProvider,
)
from src.models.candle import Candle


class CSVHistoricalDataProvider(BaseHistoricalDataProvider):
    """
    Historical data provider backed by a CSV file.
    """

    def __init__(
        self,
        csv_path: str | Path,
    ):
        """
        Initialize the provider.

        Args:
            csv_path: Path to the CSV file.
        """
        self._csv_path = Path(csv_path)

    def load(self) -> tuple[Candle, ...]:
        """
        Load historical candle data from the CSV file.

        Returns:
            Tuple of immutable candles.
        """
        candles = []

        with self._csv_path.open(
            mode="r",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                candles.append(
                    Candle(
                        datetime=datetime.fromisoformat(row["datetime"]),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    )
                )

        return tuple(candles)
