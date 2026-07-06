"""
Option Chain Snapshot CSV Loader

Broker-agnostic CSV importer for offline option chain snapshots.
"""

import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_greeks import OptionGreeks
from src.models.option_type import OptionType


class OptionChainSnapshotCsvLoader:
    """
    Loads option chain snapshots from broker-agnostic CSV files.
    """

    _REQUIRED_COLUMNS = (
        "snapshot_id",
        "timestamp",
        "underlying_symbol",
        "underlying_price",
        "expiry_date",
        "strike_price",
        "option_type",
        "lot_size",
        "option_symbol",
        "last_traded_price",
        "bid_price",
        "ask_price",
        "volume",
        "open_interest",
        "delta",
        "theta",
        "vega",
        "gamma",
        "implied_volatility",
    )

    def load_snapshots(self, csv_path: str | Path) -> tuple[OptionChainSnapshot, ...]:
        """
        Load option chain snapshots grouped by snapshot_id.
        """
        grouped_rows: dict[str, list[dict[str, str | None]]] = defaultdict(list)
        row_count = 0

        with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_columns(reader.fieldnames)

            for row_number, row in enumerate(reader, start=2):
                if self._is_blank_row(row):
                    continue

                row_count += 1
                snapshot_id = self._parse_snapshot_id(row.get("snapshot_id"), row_number)
                grouped_rows[snapshot_id].append({**row, "__row_number__": str(row_number)})

        if row_count == 0:
            raise ValueError("option chain snapshot CSV contains no rows")

        snapshots = []
        for snapshot_id, rows in grouped_rows.items():
            metadata = None
            entries = []
            for row in rows:
                row_number = int(row["__row_number__"])
                snapshot_metadata = self._build_snapshot_metadata(row, row_number)
                if metadata is None:
                    metadata = snapshot_metadata
                elif snapshot_metadata != metadata:
                    raise ValueError(
                        f"inconsistent option chain snapshot metadata for snapshot_id: {snapshot_id}"
                    )

                entries.append(self._build_entry(row, row_number))

            timestamp, underlying_symbol, underlying_price = metadata
            snapshots.append(
                OptionChainSnapshot(
                    underlying_symbol=underlying_symbol,
                    underlying_price=underlying_price,
                    timestamp=timestamp,
                    entries=tuple(entries),
                )
            )

        return tuple(sorted(snapshots, key=lambda snapshot: snapshot.timestamp))

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
                "missing required option chain snapshot CSV columns: "
                f"{', '.join(missing_columns)}"
            )

    def _is_blank_row(self, row: dict[str, str | None]) -> bool:
        """
        Return True when a CSV row is fully blank.
        """
        return all(value is None or not value.strip() for value in row.values())

    def _parse_snapshot_id(self, value: str | None, row_number: int) -> str:
        """
        Parse and validate snapshot_id.
        """
        if value is None or not value.strip():
            raise ValueError("option chain snapshot_id is required")
        return value.strip()

    def _build_snapshot_metadata(
        self,
        row: dict[str, str | None],
        row_number: int,
    ) -> tuple[datetime, str, float]:
        """
        Parse snapshot metadata for one row.
        """
        return (
            self._parse_timestamp(row.get("timestamp"), row_number),
            self._parse_string(row.get("underlying_symbol"), row_number, "underlying_symbol"),
            self._parse_float(row.get("underlying_price"), row_number, "underlying_price"),
        )

    def _build_entry(
        self,
        row: dict[str, str | None],
        row_number: int,
    ) -> OptionChainEntry:
        """
        Build one entry from a CSV row.
        """
        contract = OptionContract(
            underlying_symbol=self._parse_string(
                row.get("underlying_symbol"), row_number, "underlying_symbol"
            ),
            expiry_date=self._parse_date(row.get("expiry_date"), row_number),
            strike_price=self._parse_float(row.get("strike_price"), row_number, "strike_price"),
            option_type=self._parse_option_type(row.get("option_type"), row_number),
            lot_size=self._parse_int(row.get("lot_size"), row_number, "lot_size"),
            symbol=self._parse_string(row.get("option_symbol"), row_number, "option_symbol"),
        )

        greeks = self._parse_greeks(row, row_number)

        return OptionChainEntry(
            contract=contract,
            last_traded_price=self._parse_float(
                row.get("last_traded_price"), row_number, "last_traded_price"
            ),
            bid_price=self._parse_optional_float(row.get("bid_price"), row_number, "bid_price"),
            ask_price=self._parse_optional_float(row.get("ask_price"), row_number, "ask_price"),
            volume=self._parse_int(row.get("volume"), row_number, "volume"),
            open_interest=self._parse_int(
                row.get("open_interest"), row_number, "open_interest"
            ),
            greeks=greeks,
        )

    def _parse_timestamp(self, value: str | None, row_number: int) -> datetime:
        """
        Parse and validate timestamp.
        """
        if value is None or not value.strip():
            raise ValueError(
                f"invalid option chain snapshot timestamp at row {row_number}: {value}"
            )

        try:
            return datetime.fromisoformat(value.strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"invalid option chain snapshot timestamp at row {row_number}: {value}"
            ) from error

    def _parse_date(self, value: str | None, row_number: int) -> date:
        """
        Parse and validate expiry date.
        """
        if value is None or not value.strip():
            raise ValueError(f"invalid option expiry_date at row {row_number}: {value}")

        try:
            return date.fromisoformat(value.strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"invalid option expiry_date at row {row_number}: {value}"
            ) from error

    def _parse_option_type(self, value: str | None, row_number: int) -> OptionType:
        """
        Parse and validate option type.
        """
        if value is None or not value.strip():
            raise ValueError(
                f"invalid option chain snapshot value at row {row_number}: option_type"
            )

        normalized = value.strip().upper()
        for option_type in OptionType:
            if option_type.value == normalized:
                return option_type

        raise ValueError(
            f"invalid option chain snapshot value at row {row_number}: option_type"
        )

    def _parse_float(self, value: str | None, row_number: int, column: str) -> float:
        """
        Parse a required float value.
        """
        if value is None or not value.strip():
            raise ValueError(
                f"invalid option chain snapshot value at row {row_number}: {column}"
            )

        try:
            return float(value.strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"invalid option chain snapshot value at row {row_number}: {column}"
            ) from error

    def _parse_optional_float(
        self,
        value: str | None,
        row_number: int,
        column: str,
    ) -> float | None:
        """
        Parse an optional float value, treating blanks as None.
        """
        if value is None or not value.strip():
            return None

        try:
            return float(value.strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"invalid option chain snapshot value at row {row_number}: {column}"
            ) from error

    def _parse_int(self, value: str | None, row_number: int, column: str) -> int:
        """
        Parse an int value.
        """
        if value is None or not value.strip():
            raise ValueError(
                f"invalid option chain snapshot value at row {row_number}: {column}"
            )

        try:
            return int(value.strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"invalid option chain snapshot value at row {row_number}: {column}"
            ) from error

    def _parse_string(self, value: str | None, row_number: int, column: str) -> str:
        """
        Parse a required string value.
        """
        if value is None or not value.strip():
            raise ValueError(
                f"invalid option chain snapshot value at row {row_number}: {column}"
            )
        return value.strip()

    def _parse_greeks(
        self,
        row: dict[str, str | None],
        row_number: int,
    ) -> OptionGreeks | None:
        """
        Parse Greek values, creating greeks only when any value is supplied.
        """
        delta = self._parse_optional_float(row.get("delta"), row_number, "delta")
        theta = self._parse_optional_float(row.get("theta"), row_number, "theta")
        vega = self._parse_optional_float(row.get("vega"), row_number, "vega")
        gamma = self._parse_optional_float(row.get("gamma"), row_number, "gamma")
        implied_volatility = self._parse_optional_float(
            row.get("implied_volatility"), row_number, "implied_volatility"
        )

        if all(
            value is None
            for value in (delta, theta, vega, gamma, implied_volatility)
        ):
            return None

        return OptionGreeks(
            delta=delta,
            theta=theta,
            vega=vega,
            gamma=gamma,
            implied_volatility=implied_volatility,
        )
