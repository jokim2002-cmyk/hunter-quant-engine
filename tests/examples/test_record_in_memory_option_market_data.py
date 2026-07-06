"""Tests for the in-memory option market data recording demo."""

import io
from pathlib import Path

import pytest

from examples.record_in_memory_option_market_data import run_demo


def test_run_demo_returns_zero(tmp_path):
    assert run_demo(tmp_path) == 0


def test_run_demo_creates_snapshot_csv(tmp_path):
    run_demo(tmp_path)
    assert (tmp_path / "demo_snapshots.csv").exists()


def test_run_demo_creates_premium_csv(tmp_path):
    run_demo(tmp_path)
    assert (tmp_path / "demo_premiums.csv").exists()


def test_run_demo_snapshot_csv_is_non_empty(tmp_path):
    run_demo(tmp_path)
    assert (tmp_path / "demo_snapshots.csv").stat().st_size > 0


def test_run_demo_premium_csv_is_non_empty(tmp_path):
    run_demo(tmp_path)
    assert (tmp_path / "demo_premiums.csv").stat().st_size > 0


def test_run_demo_output_mentions_synthetic_demo(tmp_path, capsys):
    run_demo(tmp_path)
    output = capsys.readouterr().out.lower()
    assert "synthetic" in output
    assert "demo" in output


def test_run_demo_output_mentions_not_real_market_data(tmp_path, capsys):
    run_demo(tmp_path)
    output = capsys.readouterr().out.lower()
    assert "not real market data" in output


def test_run_demo_output_mentions_no_orders_placed(tmp_path, capsys):
    run_demo(tmp_path)
    output = capsys.readouterr().out.lower()
    assert "no orders placed" in output


def test_run_demo_output_mentions_not_a_profitability_claim(tmp_path, capsys):
    run_demo(tmp_path)
    output = capsys.readouterr().out.lower()
    assert "not a profitability claim" in output


def test_run_demo_output_reports_one_snapshot_recorded(tmp_path, capsys):
    run_demo(tmp_path)
    output = capsys.readouterr().out
    assert "Snapshots recorded" in output
    assert ": 1" in output


def test_run_demo_output_reports_one_candle_recorded(tmp_path, capsys):
    run_demo(tmp_path)
    output = capsys.readouterr().out
    assert "Premium candles recorded" in output
    assert ": 1" in output


def test_run_demo_creates_output_dir_if_missing(tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    assert not nested.exists()
    run_demo(nested)
    assert nested.exists()


def test_no_fyers_imports_in_demo():
    source = Path("examples/record_in_memory_option_market_data.py")
    text = source.read_text(encoding="utf-8").lower()
    assert "fyers" not in text
