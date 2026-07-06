"""
Option Chain Snapshot CSV Writer Tests
"""

import csv
from datetime import date, datetime
from pathlib import Path

import pytest

from src.backtesting.option_chain_snapshot_csv_writer import (
    OptionChainSnapshotCsvWriter,
)
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_greeks import OptionGreeks
from src.models.option_type import OptionType


def _contract(symbol, option_type, strike):
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=strike,
        option_type=option_type,
        lot_size=65,
        symbol=symbol,
    )


def _entry(symbol, option_type, strike, bid_price=99.0, ask_price=101.0, greeks=None):
    return OptionChainEntry(
        contract=_contract(symbol, option_type, strike),
        last_traded_price=100.0,
        bid_price=bid_price,
        ask_price=ask_price,
        volume=1000,
        open_interest=5000,
        greeks=greeks,
    )


def _snapshot(timestamp, entries):
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=timestamp,
        entries=entries,
    )


def test_write_snapshots_writes_header(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"

    writer.write_snapshots([_snapshot(datetime(2026, 7, 6, 9, 30), (_entry("ABC", OptionType.CE, 24200.0),))], csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[0] == [
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
    ]


def test_write_snapshots_creates_parent_directory(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "nested" / "snapshots.csv"

    writer.write_snapshots([_snapshot(datetime(2026, 7, 6, 9, 30), (_entry("ABC", OptionType.CE, 24200.0),))], csv_path)

    assert csv_path.exists()
    assert csv_path.parent.exists()


def test_write_snapshots_rejects_empty_snapshots(tmp_path):
    writer = OptionChainSnapshotCsvWriter()

    with pytest.raises(ValueError, match="option chain snapshots are required"):
        writer.write_snapshots([], tmp_path / "snapshots.csv")


def test_write_snapshots_writes_one_row_per_entry(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"
    snapshot = _snapshot(
        datetime(2026, 7, 6, 9, 30),
        (
            _entry("ABC", OptionType.CE, 24200.0),
            _entry("XYZ", OptionType.PE, 24300.0),
        ),
    )

    writer.write_snapshots([snapshot], csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert len(rows) == 3


def test_write_snapshots_sorts_snapshots_by_timestamp(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"
    snapshots = [
        _snapshot(datetime(2026, 7, 6, 10, 0), (_entry("ABC", OptionType.CE, 24200.0),)),
        _snapshot(datetime(2026, 7, 6, 9, 0), (_entry("XYZ", OptionType.PE, 24300.0),)),
    ]

    writer.write_snapshots(snapshots, csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][0] == "snapshot_1"
    assert rows[1][8] == "XYZ"
    assert rows[2][0] == "snapshot_2"
    assert rows[2][8] == "ABC"


def test_write_snapshots_preserves_entry_order_inside_snapshot(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"
    snapshot = _snapshot(
        datetime(2026, 7, 6, 9, 30),
        (
            _entry("ABC", OptionType.CE, 24200.0),
            _entry("XYZ", OptionType.PE, 24300.0),
        ),
    )

    writer.write_snapshots([snapshot], csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][8] == "ABC"
    assert rows[2][8] == "XYZ"


def test_write_snapshots_uses_deterministic_snapshot_ids(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"

    writer.write_snapshots(
        [
            _snapshot(datetime(2026, 7, 6, 9, 30), (_entry("ABC", OptionType.CE, 24200.0),)),
            _snapshot(datetime(2026, 7, 6, 10, 0), (_entry("XYZ", OptionType.PE, 24300.0),)),
        ],
        csv_path,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][0] == "snapshot_1"
    assert rows[2][0] == "snapshot_2"


def test_write_snapshots_writes_option_type_values_and_blank_bid_ask(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"

    writer.write_snapshots(
        [
            _snapshot(
                datetime(2026, 7, 6, 9, 30),
                (_entry("ABC", OptionType.CE, 24200.0, bid_price=None, ask_price=None),),
            )
        ],
        csv_path,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][6] == "ce"
    assert rows[1][10] == ""
    assert rows[1][11] == ""


def test_write_snapshots_writes_greeks_when_present(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"

    writer.write_snapshots(
        [
            _snapshot(
                datetime(2026, 7, 6, 9, 30),
                (
                    _entry(
                        "ABC",
                        OptionType.CE,
                        24200.0,
                        greeks=OptionGreeks(delta=0.2, theta=-0.1, vega=0.3, gamma=0.4, implied_volatility=0.25),
                    ),
                ),
            )
        ],
        csv_path,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][14] == "0.2"
    assert rows[1][15] == "-0.1"
    assert rows[1][16] == "0.3"
    assert rows[1][17] == "0.4"
    assert rows[1][18] == "0.25"


def test_write_snapshots_writes_blank_greek_columns_when_missing(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"

    writer.write_snapshots([_snapshot(datetime(2026, 7, 6, 9, 30), (_entry("ABC", OptionType.CE, 24200.0),))], csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][14:] == ["", "", "", "", ""]


def test_append_snapshot_creates_file_with_header(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"

    writer.append_snapshot(_snapshot(datetime(2026, 7, 6, 9, 30), (_entry("ABC", OptionType.CE, 24200.0),)), csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[0] == [
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
    ]
    assert rows[1][0] == datetime(2026, 7, 6, 9, 30).isoformat()


def test_append_snapshot_appends_without_duplicating_header(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"

    writer.append_snapshot(_snapshot(datetime(2026, 7, 6, 9, 30), (_entry("ABC", OptionType.CE, 24200.0),)), csv_path)
    writer.append_snapshot(_snapshot(datetime(2026, 7, 6, 10, 0), (_entry("XYZ", OptionType.PE, 24300.0),)), csv_path, snapshot_id="custom")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert len(rows) == 3
    assert rows[0][0] == "snapshot_id"


def test_append_snapshot_uses_provided_snapshot_id(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    csv_path = tmp_path / "snapshots.csv"

    writer.append_snapshot(_snapshot(datetime(2026, 7, 6, 9, 30), (_entry("ABC", OptionType.CE, 24200.0),)), csv_path, snapshot_id="custom")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][0] == "custom"


def test_append_snapshot_rejects_blank_snapshot_id(tmp_path):
    writer = OptionChainSnapshotCsvWriter()

    with pytest.raises(ValueError, match="option chain snapshot_id is required"):
        writer.append_snapshot(_snapshot(datetime(2026, 7, 6, 9, 30), (_entry("ABC", OptionType.CE, 24200.0),)), tmp_path / "snapshots.csv", snapshot_id=" ")


def test_writer_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(__file__).resolve().parents[1] / ".." / "src" / "backtesting" / "option_chain_snapshot_csv_writer.py"
    content = source.read_text(encoding="utf-8").lower()

    assert "fyers" not in content
