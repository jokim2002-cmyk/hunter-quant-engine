"""
Option Premium Candle CSV Loader

Broker-agnostic CSV importer for offline option premium candles.
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from src.backtesting.in_memory_option_premium_candle_provider import (
    InMemoryOptionPremiumCandleProvider,
)
from src.models.option_premium_candle import OptionPremiumCandle


class OptionPremiumCandleCsvLoader:
    """
    Loads option premium candles from broker-agnostic CSV files.
    """

    _REQUIRED_COLUMNS = ("symbol", "timestamp", "open", "high", "low", "close")

    def load_grouped_candles(
        self,
        csv_path: str | Path,
    ) -> dict[str, tuple[OptionPremiumCandle, ...]]:
        """
        Load option premium candles grouped by symbol.
        """
        grouped_candles = defaultdict(list)
        row_count = 0

        with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_columns(reader.fieldnames)

            for row_number, row in enumerate(reader, start=2):
                if self._is_blank_row(row):
                    continue

                row_count += 1
                symbol = row["symbol"].strip()
                if not symbol:
                    raise ValueError("option premium candle symbol is required")

                grouped_candles[symbol].append(
                    OptionPremiumCandle(
                        timestamp=self._parse_timestamp(row["timestamp"], row_number),
                        open=self._parse_float(row["open"], row_number, "open"),
                        high=self._parse_float(row["high"], row_number, "high"),
                        low=self._parse_float(row["low"], row_number, "low"),
                        close=self._parse_float(row["close"], row_number, "close"),
                        volume=self._parse_volume(row.get("volume"), row_number),
                    )
                )

        if row_count == 0:
            raise ValueError("option premium candle CSV contains no rows")

        return {
            symbol: tuple(sorted(candles, key=lambda candle: candle.timestamp))
            for symbol, candles in grouped_candles.items()
        }

    def load_provider(
        self,
        csv_path: str | Path,
    ) -> InMemoryOptionPremiumCandleProvider:
        """
        Load option premium candles and return an in-memory provider.
        """
        return InMemoryOptionPremiumCandleProvider(
            self.load_grouped_candles(csv_path)
        )

    def _validate_columns(
        self,
        fieldnames: list[str] | None,
    ) -> None:
        """
        Validate required CSV columns.
        """
        existing_columns = set(fieldnames or ())
        missing_columns = tuple(
            column for column in self._REQUIRED_COLUMNS if column not in existing_columns
        )
        if missing_columns:
            raise ValueError(
                "missing required option premium candle CSV columns: "
                f"{', '.join(missing_columns)}"
            )

    def _is_blank_row(
        self,
        row: dict[str, str | None],
    ) -> bool:
        """
        Return True when a CSV row is fully blank.
        """
        return all(value is None or not value.strip() for value in row.values())

    def _parse_timestamp(
        self,
        value: str,
        row_number: int,
    ) -> datetime:
        """
        Parse an ISO timestamp with row-aware errors.
        """
        try:
            return datetime.fromisoformat(value.strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"invalid timestamp at row {row_number}: {value}"
            ) from error

    def _parse_float(
        self,
        value: str,
        row_number: int,
        column: str,
    ) -> float:
        """
        Parse a float with row-aware errors.
        """
        try:
            return float(value.strip())
        except (AttributeError, ValueError) as error:
            raise ValueError(
                f"invalid option premium candle value at row {row_number}: {column}"
            ) from error

    def _parse_volume(
        self,
        value: str | None,
        row_number: int,
    ) -> int:
        """
        Parse volume, defaulting missing or blank values to zero.
        """
        if value is None or not value.strip():
            return 0

        try:
            return int(value.strip())
        except ValueError as error:
            raise ValueError(
                f"invalid option premium candle value at row {row_number}: volume"
            ) from error
