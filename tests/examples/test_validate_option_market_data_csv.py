"""Tests for the CSV validation demo script. Synthetic data only. No FYERS."""

from pathlib import Path

from examples.record_in_memory_option_market_data import run_demo as run_recording_demo
from examples.validate_option_market_data_csv import run_demo


def _prepare_csvs(tmp_path) -> tuple[Path, Path]:
    """Write synthetic CSV files using the recording demo into tmp_path."""
    run_recording_demo(tmp_path)
    return tmp_path / "demo_snapshots.csv", tmp_path / "demo_premiums.csv"


# ---------------------------------------------------------------------------
# Return code
# ---------------------------------------------------------------------------

def test_valid_csvs_return_zero(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    assert run_demo(snapshot_csv, premium_csv) == 0


def test_missing_snapshot_returns_nonzero(tmp_path, capsys):
    _, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    assert run_demo(tmp_path / "missing.csv", premium_csv) != 0


def test_missing_premium_returns_nonzero(tmp_path, capsys):
    snapshot_csv, _ = _prepare_csvs(tmp_path)
    capsys.readouterr()
    assert run_demo(snapshot_csv, tmp_path / "missing.csv") != 0


def test_invalid_csv_returns_nonzero(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    snapshot_csv.write_text("", encoding="utf-8")
    assert run_demo(snapshot_csv, premium_csv) != 0


# ---------------------------------------------------------------------------
# Valid output content
# ---------------------------------------------------------------------------

def test_output_says_validation_passed(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    assert "csv validation passed" in capsys.readouterr().out.lower()


def test_output_includes_snapshot_count(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    assert "snapshot count" in capsys.readouterr().out.lower()


def test_output_includes_premium_candle_count(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    assert "premium candle count" in capsys.readouterr().out.lower()


def test_output_includes_symbols(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    assert "symbols" in capsys.readouterr().out.lower()


def test_output_mentions_synthetic_demo(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    output = capsys.readouterr().out.lower()
    assert "synthetic" in output
    assert "demo" in output


def test_output_says_no_orders_placed(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    assert "no orders placed" in capsys.readouterr().out.lower()


def test_output_says_not_live_market_data(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    assert "not live market data" in capsys.readouterr().out.lower()


def test_output_says_not_a_profitability_claim(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    assert "not a profitability claim" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------------------
# Invalid CSV output
# ---------------------------------------------------------------------------

def test_invalid_csv_output_says_validation_failed(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    snapshot_csv.write_text("", encoding="utf-8")
    run_demo(snapshot_csv, premium_csv)
    assert "csv validation failed" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------------------
# Missing files instruction
# ---------------------------------------------------------------------------

def test_missing_files_output_mentions_recording_demo(tmp_path, capsys):
    run_demo(tmp_path / "no_snap.csv", tmp_path / "no_prem.csv")
    assert "record_in_memory_option_market_data.py" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Broker-agnostic guard
# ---------------------------------------------------------------------------

def test_no_fyers_in_validation_demo():
    source = Path("examples/validate_option_market_data_csv.py")
    assert "fyers" not in source.read_text(encoding="utf-8").lower()
