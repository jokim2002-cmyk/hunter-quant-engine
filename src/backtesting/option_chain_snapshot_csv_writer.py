"""
Option Chain Snapshot CSV Writer

Broker-agnostic CSV exporter for option chain snapshots.
"""

import csv
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_greeks import OptionGreeks


class OptionChainSnapshotCsvWriter:
    """
    Writes option chain snapshots to a broker-agnostic CSV file.
    """

    _HEADER = (
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

    def write_snapshots(
        self,
        snapshots: Sequence[OptionChainSnapshot],
        csv_path: str | Path,
    ) -> None:
        """
        Write one row per snapshot entry to a CSV file.
        """
        if not snapshots:
            raise ValueError("option chain snapshots are required")

        output_path = Path(csv_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ordered_snapshots = sorted(snapshots, key=lambda snapshot: snapshot.timestamp)
        rows = []
        for index, snapshot in enumerate(ordered_snapshots, start=1):
            snapshot_id = f"snapshot_{index}"
            for entry in snapshot.entries:
                rows.append(self._row(snapshot_id, snapshot, entry))

        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self._HEADER)
            writer.writerows(rows)

    def append_snapshot(
        self,
        snapshot: OptionChainSnapshot,
        csv_path: str | Path,
        snapshot_id: str | None = None,
    ) -> None:
        """
        Append snapshot rows to an existing CSV file.
        """
        if snapshot_id is None:
            snapshot_id = snapshot.timestamp.isoformat()
        if not snapshot_id.strip():
            raise ValueError("option chain snapshot_id is required")

        output_path = Path(csv_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rows_to_write = []
        if not output_path.exists() or output_path.stat().st_size == 0:
            rows_to_write.append(list(self._HEADER))

        for entry in snapshot.entries:
            rows_to_write.append(self._row(snapshot_id, snapshot, entry))

        with output_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if not rows_to_write or rows_to_write[0] == list(self._HEADER):
                writer.writerow(self._HEADER)
                rows_to_write = rows_to_write[1:]
            writer.writerows(rows_to_write)

    def _row(
        self,
        snapshot_id: str,
        snapshot: OptionChainSnapshot,
        entry,
    ) -> list[object]:
        greeks = entry.greeks
        if greeks is None:
            delta = theta = vega = gamma = implied_volatility = ""
        else:
            delta = greeks.delta if greeks.delta is not None else ""
            theta = greeks.theta if greeks.theta is not None else ""
            vega = greeks.vega if greeks.vega is not None else ""
            gamma = greeks.gamma if greeks.gamma is not None else ""
            implied_volatility = (
                greeks.implied_volatility
                if greeks.implied_volatility is not None
                else ""
            )

        bid_price = entry.bid_price if entry.bid_price is not None else ""
        ask_price = entry.ask_price if entry.ask_price is not None else ""

        return [
            snapshot_id,
            snapshot.timestamp.isoformat(),
            snapshot.underlying_symbol,
            snapshot.underlying_price,
            entry.contract.expiry_date.isoformat(),
            entry.contract.strike_price,
            entry.contract.option_type.value.lower(),
            entry.contract.lot_size,
            entry.contract.symbol,
            entry.last_traded_price,
            bid_price,
            ask_price,
            entry.volume,
            entry.open_interest,
            delta,
            theta,
            vega,
            gamma,
            implied_volatility,
        ]
