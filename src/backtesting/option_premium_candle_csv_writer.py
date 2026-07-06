"""
Option Premium Candle CSV Writer

Broker-agnostic CSV exporter for offline option premium candles.
"""

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from src.models.option_premium_candle import OptionPremiumCandle


class OptionPremiumCandleCsvWriter:
    """
    Writes option premium candles to broker-agnostic CSV files.
    """

    _HEADER = (
        "symbol",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )

    def write_grouped_candles(
        self,
        candle_data_by_symbol: Mapping[str, Sequence[OptionPremiumCandle]],
        csv_path: str | Path,
    ) -> None:
        """
        Write grouped candles to a CSV file with deterministic ordering.
        """
        output_path = Path(csv_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for symbol in sorted(candle_data_by_symbol):
            candles = tuple(candle_data_by_symbol[symbol])
            if not symbol.strip():
                raise ValueError("option premium candle symbol is required")
            if not candles:
                raise ValueError(f"option premium candles are required for symbol: {symbol}")

            for candle in sorted(candles, key=lambda item: item.timestamp):
                rows.append(
                    (
                        symbol,
                        candle.timestamp.isoformat(),
                        candle.open,
                        candle.high,
                        candle.low,
                        candle.close,
                        candle.volume,
                    )
                )

        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self._HEADER)
            writer.writerows(rows)

    def append_candles(
        self,
        symbol: str,
        candles: Sequence[OptionPremiumCandle],
        csv_path: str | Path,
    ) -> None:
        """
        Append candles for one symbol to a CSV file.
        """
        if not symbol.strip():
            raise ValueError("option premium candle symbol is required")
        if not candles:
            raise ValueError(f"option premium candles are required for symbol: {symbol}")

        output_path = Path(csv_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        existing_rows = []
        if output_path.exists() and output_path.stat().st_size > 0:
            with output_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                existing_rows = list(reader)

        rows_to_write = []
        if not existing_rows:
            rows_to_write.append(list(self._HEADER))

        for candle in sorted(candles, key=lambda item: item.timestamp):
            rows_to_write.append(
                [
                    symbol,
                    candle.timestamp.isoformat(),
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                ]
            )

        with output_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if not existing_rows:
                writer.writerow(self._HEADER)
            writer.writerows(rows_to_write[1:] if not existing_rows else rows_to_write)
