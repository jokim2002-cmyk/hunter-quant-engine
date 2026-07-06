"""End-to-end smoke test for the safe offline demo workflow.

Proves the full beginner workflow works safely:
  Step 1 - record_in_memory_option_market_data.py creates synthetic CSV files.
  Step 2 - validate_option_market_data_csv.py validates those CSV files.
  Step 3 - replay_csv_option_market_data.py replays those CSV files offline.

Synthetic/demo data only. No broker code. No orders placed.
Not live market data. Not a profitability claim.
"""

from pathlib import Path

from examples.record_in_memory_option_market_data import run_demo as run_recording_demo
from examples.replay_csv_option_market_data import run_demo as run_replay_demo
from examples.validate_option_market_data_csv import run_demo as run_validation_demo


def test_full_record_validate_replay_workflow(tmp_path, capsys):
    snapshot_csv = tmp_path / "demo_snapshots.csv"
    premium_csv = tmp_path / "demo_premiums.csv"

    # Step 1 — record
    assert run_recording_demo(tmp_path) == 0
    assert snapshot_csv.exists()
    assert premium_csv.exists()

    capsys.readouterr()  # discard recording output

    # Step 2 — validate
    assert run_validation_demo(snapshot_csv, premium_csv) == 0
    validation_output = capsys.readouterr().out.lower()
    assert "csv validation passed" in validation_output
    assert "synthetic" in validation_output
    assert "no orders placed" in validation_output
    assert "not live market data" in validation_output
    assert "not a profitability claim" in validation_output

    # Step 3 — replay
    assert run_replay_demo(snapshot_csv, premium_csv) == 0
    replay_output = capsys.readouterr().out.lower()
    assert "csv replay" in replay_output
    assert "synthetic" in replay_output
    assert "no orders placed" in replay_output
    assert "not live market data" in replay_output
    assert "not a profitability claim" in replay_output


def test_no_broker_imports_in_example_scripts():
    """Guard: none of the three demo scripts import any broker SDK."""
    scripts = [
        Path("examples/record_in_memory_option_market_data.py"),
        Path("examples/validate_option_market_data_csv.py"),
        Path("examples/replay_csv_option_market_data.py"),
    ]
    forbidden = "fy" + "ers"
    for script in scripts:
        assert forbidden not in script.read_text(encoding="utf-8").lower(), script
