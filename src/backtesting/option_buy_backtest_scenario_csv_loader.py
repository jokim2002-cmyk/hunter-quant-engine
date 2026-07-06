"""
Option Buy Backtest Scenario CSV Loader

Broker-agnostic CSV importer for offline option-buy backtest scenarios.
"""

import csv
from collections import OrderedDict
from datetime import date, datetime
from pathlib import Path

from src.backtesting.option_buy_backtest_scenario import OptionBuyBacktestScenario
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_greeks import OptionGreeks
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal


class OptionBuyBacktestScenarioCsvLoader:
    """
    Loads TradeSignal and OptionChainSnapshot pairs from CSV rows.
    """

    _REQUIRED_COLUMNS = (
        "snapshot_id",
        "timestamp",
        "signal_type",
        "signal_strength",
        "confidence",
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
    )
    _GREEK_COLUMNS = ("delta", "theta", "vega", "gamma", "implied_volatility")

    def load_scenarios(
        self,
        csv_path: str | Path,
    ) -> tuple[OptionBuyBacktestScenario, ...]:
        """
        Load option-buy backtest scenarios from a CSV file.
        """
        grouped_rows = OrderedDict()
        row_count = 0

        with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_columns(reader.fieldnames)

            for row_number, row in enumerate(reader, start=2):
                if self._is_blank_row(row):
                    continue

                row_count += 1
                snapshot_id = row["snapshot_id"].strip()
                if not snapshot_id:
                    raise ValueError("scenario snapshot_id is required")

                parsed_row = self._parse_row(row, row_number)
                if snapshot_id not in grouped_rows:
                    grouped_rows[snapshot_id] = {
                        "metadata": parsed_row["metadata"],
                        "entries": [],
                    }
                elif grouped_rows[snapshot_id]["metadata"] != parsed_row["metadata"]:
                    raise ValueError(
                        "inconsistent scenario snapshot metadata for snapshot_id: "
                        f"{snapshot_id}"
                    )

                grouped_rows[snapshot_id]["entries"].append(parsed_row["entry"])

        if row_count == 0:
            raise ValueError("option buy backtest scenario CSV contains no rows")

        scenarios = []
        for group in grouped_rows.values():
            metadata = group["metadata"]
            signal = TradeSignal(
                signal_type=metadata["signal_type"],
                strength=metadata["signal_strength"],
                confidence=metadata["confidence"],
                rationale=metadata["rationale"],
                created_at=metadata["timestamp"],
            )
            snapshot = OptionChainSnapshot(
                underlying_symbol=metadata["underlying_symbol"],
                underlying_price=metadata["underlying_price"],
                timestamp=metadata["timestamp"],
                entries=tuple(group["entries"]),
            )
            scenarios.append(OptionBuyBacktestScenario(signal=signal, snapshot=snapshot))

        return tuple(sorted(scenarios, key=lambda scenario: scenario.snapshot.timestamp))

    def _validate_columns(
        self,
        fieldnames: list[str] | None,
    ) -> None:
        """
        Validate required scenario CSV columns.
        """
        existing_columns = set(fieldnames or ())
        missing_columns = tuple(
            column for column in self._REQUIRED_COLUMNS if column not in existing_columns
        )
        if missing_columns:
            raise ValueError(
                "missing required option buy backtest scenario CSV columns: "
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

    def _parse_row(
        self,
        row: dict[str, str | None],
        row_number: int,
    ) -> dict[str, object]:
        """
        Parse one CSV row into metadata and one option chain entry.
        """
        timestamp = self._parse_timestamp(row["timestamp"], row_number)
        signal_type = self._parse_enum(
            row["signal_type"],
            SignalType,
            row_number,
            "signal_type",
        )
        signal_strength = self._parse_enum(
            row["signal_strength"],
            SignalStrength,
            row_number,
            "signal_strength",
        )
        confidence = self._parse_float(row["confidence"], row_number, "confidence")
        underlying_symbol = row["underlying_symbol"].strip()
        underlying_price = self._parse_float(
            row["underlying_price"], row_number, "underlying_price"
        )
        expiry_date = self._parse_date(row["expiry_date"], row_number)
        strike_price = self._parse_float(row["strike_price"], row_number, "strike_price")
        option_type = self._parse_enum(
            row["option_type"],
            OptionType,
            row_number,
            "option_type",
        )
        lot_size = self._parse_int(row["lot_size"], row_number, "lot_size")
        option_symbol = row["option_symbol"].strip()
        if not option_symbol:
            raise ValueError("option_symbol is required")

        metadata = {
            "timestamp": timestamp,
            "signal_type": signal_type,
            "signal_strength": signal_strength,
            "confidence": confidence,
            "underlying_symbol": underlying_symbol,
            "underlying_price": underlying_price,
            "rationale": self._parse_rationale(row.get("rationale")),
        }
        contract = OptionContract(
            underlying_symbol=underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strike_price,
            option_type=option_type,
            lot_size=lot_size,
            symbol=option_symbol,
        )
        entry = OptionChainEntry(
            contract=contract,
            last_traded_price=self._parse_float(
                row["last_traded_price"], row_number, "last_traded_price"
            ),
            bid_price=self._parse_optional_float(
                row["bid_price"], row_number, "bid_price"
            ),
            ask_price=self._parse_optional_float(
                row["ask_price"], row_number, "ask_price"
            ),
            volume=self._parse_int(row["volume"], row_number, "volume"),
            open_interest=self._parse_int(
                row["open_interest"], row_number, "open_interest"
            ),
            greeks=self._parse_greeks(row, row_number),
        )
        return {"metadata": metadata, "entry": entry}

    def _parse_timestamp(
        self,
        value: str,
        row_number: int,
    ) -> datetime:
        """
        Parse timestamp with row-aware errors.
        """
        try:
            return datetime.fromisoformat(value.strip())
        except (AttributeError, ValueError) as error:
            raise ValueError(
                f"invalid scenario timestamp at row {row_number}: {value}"
            ) from error

    def _parse_date(
        self,
        value: str,
        row_number: int,
    ) -> date:
        """
        Parse expiry date with row-aware errors.
        """
        try:
            return date.fromisoformat(value.strip())
        except (AttributeError, ValueError) as error:
            raise ValueError(
                f"invalid option expiry_date at row {row_number}: {value}"
            ) from error

    def _parse_enum(
        self,
        value: str,
        enum_type,
        row_number: int,
        column: str,
    ):
        """
        Parse enum by value or name, case-insensitively.
        """
        normalized_value = value.strip().lower()
        for enum_value in enum_type:
            if (
                enum_value.value.lower() == normalized_value
                or enum_value.name.lower() == normalized_value
            ):
                return enum_value

        raise ValueError(
            f"invalid option buy backtest scenario value at row {row_number}: {column}"
        )

    def _parse_float(
        self,
        value: str,
        row_number: int,
        column: str,
    ) -> float:
        """
        Parse required float with row-aware errors.
        """
        try:
            return float(value.strip())
        except (AttributeError, ValueError) as error:
            raise ValueError(
                f"invalid option buy backtest scenario value at row {row_number}: "
                f"{column}"
            ) from error

    def _parse_optional_float(
        self,
        value: str | None,
        row_number: int,
        column: str,
    ) -> float | None:
        """
        Parse optional float where blank means None.
        """
        if value is None or not value.strip():
            return None

        return self._parse_float(value, row_number, column)

    def _parse_int(
        self,
        value: str,
        row_number: int,
        column: str,
    ) -> int:
        """
        Parse required integer with row-aware errors.
        """
        try:
            return int(value.strip())
        except (AttributeError, ValueError) as error:
            raise ValueError(
                f"invalid option buy backtest scenario value at row {row_number}: "
                f"{column}"
            ) from error

    def _parse_rationale(
        self,
        value: str | None,
    ) -> tuple[str, ...]:
        """
        Parse optional rationale.
        """
        if value is None or not value.strip():
            return ()

        return (value.strip(),)

    def _parse_greeks(
        self,
        row: dict[str, str | None],
        row_number: int,
    ) -> OptionGreeks | None:
        """
        Parse optional Greeks. Missing or blank Greek values become None.
        """
        greek_values = {
            column: self._parse_optional_float(row.get(column), row_number, column)
            for column in self._GREEK_COLUMNS
        }
        if all(value is None for value in greek_values.values()):
            return None

        return OptionGreeks(
            delta=greek_values["delta"],
            theta=greek_values["theta"],
            vega=greek_values["vega"],
            gamma=greek_values["gamma"],
            implied_volatility=greek_values["implied_volatility"],
        )
