"""Tests for the CSV replay option market data demo."""

from pathlib import Path

from examples.record_in_memory_option_market_data import run_demo as run_recording_demo
from examples.replay_csv_option_market_data import run_demo


def _prepare_csvs(tmp_path) -> tuple[Path, Path]:
    """Write synthetic CSV files using the recording demo into tmp_path."""
    run_recording_demo(tmp_path)
    return tmp_path / "demo_snapshots.csv", tmp_path / "demo_premiums.csv"


# ---------------------------------------------------------------------------
# Return code
# ---------------------------------------------------------------------------

def test_run_demo_returns_zero(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()  # discard recording output
    assert run_demo(snapshot_csv, premium_csv) == 0


def test_run_demo_returns_nonzero_when_snapshot_csv_missing(tmp_path, capsys):
    _, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    assert run_demo(tmp_path / "missing.csv", premium_csv) != 0


def test_run_demo_returns_nonzero_when_premium_csv_missing(tmp_path, capsys):
    snapshot_csv, _ = _prepare_csvs(tmp_path)
    capsys.readouterr()
    assert run_demo(snapshot_csv, tmp_path / "missing.csv") != 0


# ---------------------------------------------------------------------------
# Output content
# ---------------------------------------------------------------------------

def test_output_mentions_csv_replay(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    output = capsys.readouterr().out.lower()
    assert "csv replay" in output


def test_output_mentions_synthetic_demo(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    output = capsys.readouterr().out.lower()
    assert "synthetic" in output
    assert "demo" in output


def test_output_mentions_not_live_market_data(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    output = capsys.readouterr().out.lower()
    assert "not live market data" in output


def test_output_mentions_no_orders_placed(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    output = capsys.readouterr().out.lower()
    assert "no orders placed" in output


def test_output_mentions_not_a_profitability_claim(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    output = capsys.readouterr().out.lower()
    assert "not a profitability claim" in output


def test_output_includes_snapshot_summary(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    output = capsys.readouterr().out
    assert "Snapshot loaded" in output
    assert "NIFTY" in output


def test_output_includes_premium_candles_summary(tmp_path, capsys):
    snapshot_csv, premium_csv = _prepare_csvs(tmp_path)
    capsys.readouterr()
    run_demo(snapshot_csv, premium_csv)
    output = capsys.readouterr().out
    assert "Premium candles loaded" in output
    assert "1" in output


# ---------------------------------------------------------------------------
# Missing files instruction
# ---------------------------------------------------------------------------

def test_missing_files_output_mentions_recording_demo(tmp_path, capsys):
    run_demo(tmp_path / "no_snap.csv", tmp_path / "no_prem.csv")
    output = capsys.readouterr().out
    assert "record_in_memory_option_market_data.py" in output


# ---------------------------------------------------------------------------
# Broker-agnostic guard
# ---------------------------------------------------------------------------

def test_no_fyers_imports_in_replay_demo():
    source = Path("examples/replay_csv_option_market_data.py")
    text = source.read_text(encoding="utf-8").lower()
    assert "fyers" not in text
