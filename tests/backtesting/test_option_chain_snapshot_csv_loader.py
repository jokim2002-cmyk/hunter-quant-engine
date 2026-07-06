"""
Option Chain Snapshot CSV Loader Tests
"""

import csv
from datetime import date, datetime
from pathlib import Path

import pytest

from src.backtesting.option_chain_snapshot_csv_loader import (
    OptionChainSnapshotCsvLoader,
)
from src.backtesting.option_chain_snapshot_csv_writer import (
    OptionChainSnapshotCsvWriter,
)
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_greeks import OptionGreeks
from src.models.option_type import OptionType


def _write_csv(tmp_path, content):
    csv_path = tmp_path / "snapshots.csv"
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


def test_loader_reads_one_snapshot(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,CE,65,ABC,100.0,99.0,101.0,1000,5000,0.2,-0.1,0.3,0.4,0.25
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.timestamp == datetime(2026, 7, 6, 9, 30)
    assert snapshot.underlying_symbol == "NIFTY"
    assert snapshot.underlying_price == 24210.0
    assert len(snapshot.entries) == 1
    entry = snapshot.entries[0]
    assert entry.contract.option_type is OptionType.CE
    assert entry.contract.strike_price == 24200.0
    assert entry.bid_price == 99.0
    assert entry.ask_price == 101.0


def test_loader_groups_multiple_entries_into_one_snapshot(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24300.0,pe,65,XYZ,110.0,108.0,112.0,1200,6000,0.1,-0.2,0.4,0.5,0.2
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    assert len(snapshots) == 1
    assert len(snapshots[0].entries) == 2


def test_loader_returns_snapshots_sorted_by_timestamp(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_2,2026-07-06T10:00:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
snapshot_1,2026-07-06T09:00:00,NIFTY,24210.0,2026-07-09,24300.0,pe,65,XYZ,110.0,108.0,112.0,1200,6000,,,,,
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    assert [snapshot.timestamp for snapshot in snapshots] == [
        datetime(2026, 7, 6, 9, 0),
        datetime(2026, 7, 6, 10, 0),
    ]


def test_loader_preserves_entry_order_inside_snapshot(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24300.0,pe,65,XYZ,110.0,108.0,112.0,1200,6000,,,,,
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    assert [entry.contract.symbol for entry in snapshots[0].entries] == ["ABC", "XYZ"]


def test_loader_parses_ce_option(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    assert snapshots[0].entries[0].contract.option_type is OptionType.CE


def test_loader_parses_pe_option(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,PE,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    assert snapshots[0].entries[0].contract.option_type is OptionType.PE


def test_loader_parses_bid_and_ask_prices(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    assert snapshots[0].entries[0].bid_price == 99.0
    assert snapshots[0].entries[0].ask_price == 101.0


def test_loader_parses_blank_bid_and_ask_as_none(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,, ,1000,5000,,,,,
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    assert snapshots[0].entries[0].bid_price is None
    assert snapshots[0].entries[0].ask_price is None


def test_loader_parses_greeks_when_present(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,0.2,-0.1,0.3,0.4,0.25
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    greeks = snapshots[0].entries[0].greeks
    assert greeks is not None
    assert greeks.delta == 0.2
    assert greeks.theta == -0.1
    assert greeks.vega == 0.3
    assert greeks.gamma == 0.4
    assert greeks.implied_volatility == 0.25


def test_loader_uses_greeks_none_when_greek_columns_are_blank(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
""",
    )

    snapshots = loader.load_snapshots(csv_path)

    assert snapshots[0].entries[0].greeks is None


def test_loader_rejects_missing_required_columns(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000
""",
    )

    with pytest.raises(ValueError, match="missing required option chain snapshot CSV columns: delta, theta, vega, gamma, implied_volatility"):
        loader.load_snapshots(csv_path)


def test_loader_rejects_empty_csv_data_rows(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
""",
    )

    with pytest.raises(ValueError, match="option chain snapshot CSV contains no rows"):
        loader.load_snapshots(csv_path)


def test_loader_rejects_blank_snapshot_id(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
 ,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
""",
    )

    with pytest.raises(ValueError, match="option chain snapshot_id is required"):
        loader.load_snapshots(csv_path)


def test_loader_rejects_invalid_timestamp(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,not-a-date,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
""",
    )

    with pytest.raises(ValueError, match="invalid option chain snapshot timestamp at row 2: not-a-date"):
        loader.load_snapshots(csv_path)


def test_loader_rejects_invalid_expiry_date(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,not-a-date,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
""",
    )

    with pytest.raises(ValueError, match="invalid option expiry_date at row 2: not-a-date"):
        loader.load_snapshots(csv_path)


def test_loader_rejects_invalid_numeric_value(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,not-a-number,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
""",
    )

    with pytest.raises(ValueError, match="invalid option chain snapshot value at row 2: underlying_price"):
        loader.load_snapshots(csv_path)


def test_loader_rejects_invalid_option_type_enum(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,foo,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
""",
    )

    with pytest.raises(ValueError, match="invalid option chain snapshot value at row 2: option_type"):
        loader.load_snapshots(csv_path)


def test_loader_rejects_inconsistent_metadata(tmp_path):
    loader = OptionChainSnapshotCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
snapshot_1,2026-07-06T09:30:00,NIFTY,24210.0,2026-07-09,24200.0,ce,65,ABC,100.0,99.0,101.0,1000,5000,,,,,
snapshot_1,2026-07-06T09:30:00,BANKNIFTY,24210.0,2026-07-09,24300.0,pe,65,XYZ,110.0,108.0,112.0,1200,6000,,,,,
""",
    )

    with pytest.raises(ValueError, match="inconsistent option chain snapshot metadata for snapshot_id: snapshot_1"):
        loader.load_snapshots(csv_path)


def test_writer_csv_can_be_loaded_by_loader(tmp_path):
    writer = OptionChainSnapshotCsvWriter()
    loader = OptionChainSnapshotCsvLoader()
    csv_path = tmp_path / "snapshots.csv"
    snapshot = OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=datetime(2026, 7, 6, 9, 30),
        entries=(
            OptionChainEntry(
                contract=OptionContract(
                    underlying_symbol="NIFTY",
                    expiry_date=date(2026, 7, 9),
                    strike_price=24200.0,
                    option_type=OptionType.CE,
                    lot_size=65,
                    symbol="ABC",
                ),
                last_traded_price=100.0,
                bid_price=99.0,
                ask_price=101.0,
                volume=1000,
                open_interest=5000,
                greeks=OptionGreeks(delta=0.2, theta=-0.1, vega=0.3, gamma=0.4, implied_volatility=0.25),
            ),
        ),
    )

    writer.write_snapshots([snapshot], csv_path)
    loaded_snapshots = loader.load_snapshots(csv_path)

    assert len(loaded_snapshots) == 1
    assert loaded_snapshots[0].timestamp == snapshot.timestamp
    assert loaded_snapshots[0].underlying_symbol == snapshot.underlying_symbol
    assert loaded_snapshots[0].underlying_price == snapshot.underlying_price
    assert len(loaded_snapshots[0].entries) == 1
    assert loaded_snapshots[0].entries[0].contract.symbol == "ABC"
    assert loaded_snapshots[0].entries[0].greeks is not None


def test_loader_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(__file__).resolve().parents[1] / ".." / "src" / "backtesting" / "option_chain_snapshot_csv_loader.py"
    content = source.read_text(encoding="utf-8").lower()

    assert "fyers" not in content
