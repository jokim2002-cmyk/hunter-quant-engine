"""
Trade Signal CSV Loader

Broker-agnostic CSV importer for offline trade signals.
"""

import csv
from datetime import datetime
from pathlib import Path

from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal


class TradeSignalCsvLoader:
    """
    Loads trade signals from broker-agnostic CSV files.
    """

    _REQUIRED_COLUMNS = ("timestamp", "signal_type", "signal_strength", "confidence")

    def load_signals(self, csv_path: str | Path) -> tuple[TradeSignal, ...]:
        """
        Load trade signals from a CSV file.
        """
        signals = []
        row_count = 0

        with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_columns(reader.fieldnames)

            for row_number, row in enumerate(reader, start=2):
                if self._is_blank_row(row):
                    continue

                row_count += 1
                signals.append(self._parse_signal(row, row_number))

        if row_count == 0:
            raise ValueError("trade signal CSV contains no rows")

        return tuple(sorted(signals, key=lambda signal: signal.created_at))

    def _validate_columns(self, fieldnames: list[str] | None) -> None:
        """
        Validate required CSV columns.
        """
        existing_columns = set(fieldnames or ())
        missing_columns = tuple(
            column for column in self._REQUIRED_COLUMNS if column not in existing_columns
        )
        if missing_columns:
            raise ValueError(
                "missing required trade signal CSV columns: "
                f"{', '.join(missing_columns)}"
            )

    def _is_blank_row(self, row: dict[str, str | None]) -> bool:
        """
        Return True when a CSV row is fully blank.
        """
        return all(value is None or not value.strip() for value in row.values())

    def _parse_signal(self, row: dict[str, str | None], row_number: int) -> TradeSignal:
        """
        Parse one CSV row into a TradeSignal.
        """
        created_at = self._parse_timestamp(row.get("timestamp"), row_number)
        signal_type = self._parse_enum(
            row.get("signal_type"),
            SignalType,
            row_number,
            "signal_type",
        )
        signal_strength = self._parse_enum(
            row.get("signal_strength"),
            SignalStrength,
            row_number,
            "signal_strength",
        )
        confidence = self._parse_float(row.get("confidence"), row_number, "confidence")
        rationale = self._parse_rationale(row.get("rationale"))

        return TradeSignal(
            signal_type=signal_type,
            strength=signal_strength,
            confidence=confidence,
            rationale=rationale,
            created_at=created_at,
        )

    def _parse_timestamp(self, value: str | None, row_number: int) -> datetime:
        """
        Parse timestamp with row-aware errors.
        """
        if value is None or not value.strip():
            raise ValueError(
                f"invalid trade signal timestamp at row {row_number}: {value}"
            )

        try:
            return datetime.fromisoformat(value.strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"invalid trade signal timestamp at row {row_number}: {value}"
            ) from error

    def _parse_enum(
        self,
        value: str | None,
        enum_type,
        row_number: int,
        column: str,
    ):
        """
        Parse enum values case-insensitively.
        """
        if value is None or not value.strip():
            raise ValueError(f"invalid trade signal value at row {row_number}: {column}")

        normalized_value = value.strip().lower()
        for enum_value in enum_type:
            if (
                enum_value.value.lower() == normalized_value
                or enum_value.name.lower() == normalized_value
            ):
                return enum_value

        raise ValueError(f"invalid trade signal value at row {row_number}: {column}")

    def _parse_float(self, value: str | None, row_number: int, column: str) -> float:
        """
        Parse a required float value.
        """
        if value is None or not value.strip():
            raise ValueError(f"invalid trade signal value at row {row_number}: {column}")

        try:
            return float(value.strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"invalid trade signal value at row {row_number}: {column}"
            ) from error

    def _parse_rationale(self, value: str | None) -> tuple[str, ...]:
        """
        Parse rationale into a tuple of strings.
        """
        if value is None or not value.strip():
            return ()

        return (value.strip(),)
