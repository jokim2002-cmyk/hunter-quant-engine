"""Tests for option_market_data_csv_validator. Synthetic data only. No FYERS."""

from datetime import date, datetime
from pathlib import Path

from src.data_recording.csv_option_market_data_recorder import CsvOptionMarketDataRecorder
from src.data_recording.option_market_data_csv_validator import (
    OptionMarketDataCsvValidationResult,
    validate_option_market_data_csvs,
)
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SYMBOL = "NIFTY_VAL_24200CE"


def _snapshot() -> OptionChainSnapshot:
    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 31),
        strike_price=24200,
        option_type=OptionType.CE,
        lot_size=75,
        symbol=SYMBOL,
    )
    entry = OptionChainEntry(
        contract=contract,
        last_traded_price=120.0,
        bid_price=119.5,
        ask_price=120.5,
        volume=500,
        open_interest=10000,
    )
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=datetime(2026, 7, 6, 9, 15),
        entries=(entry,),
    )


def _candle() -> OptionPremiumCandle:
    return OptionPremiumCandle(
        timestamp=datetime(2026, 7, 6, 9, 15),
        open=115.0,
        high=122.0,
        low=113.0,
        close=118.0,
        volume=200,
    )


def _write_csvs(tmp_path) -> tuple[Path, Path]:
    snapshot_csv = tmp_path / "snapshots.csv"
    premium_csv = tmp_path / "premiums.csv"
    recorder = CsvOptionMarketDataRecorder(
        snapshot_csv_path=snapshot_csv,
        premium_csv_path=premium_csv,
    )
    recorder.record_snapshot(_snapshot(), snapshot_id="val-001")
    recorder.record_premium_candles(SYMBOL, (_candle(),))
    return snapshot_csv, premium_csv


# ---------------------------------------------------------------------------
# Valid CSVs
# ---------------------------------------------------------------------------

def test_valid_csvs_return_is_valid_true(tmp_path):
    snapshot_csv, premium_csv = _write_csvs(tmp_path)
    result = validate_option_market_data_csvs(snapshot_csv, premium_csv)
    assert result.is_valid is True
    assert result.errors == []


def test_valid_csvs_count_snapshots(tmp_path):
    snapshot_csv, premium_csv = _write_csvs(tmp_path)
    result = validate_option_market_data_csvs(snapshot_csv, premium_csv)
    assert result.snapshot_count == 1


def test_valid_csvs_count_premium_candles(tmp_path):
    snapshot_csv, premium_csv = _write_csvs(tmp_path)
    result = validate_option_market_data_csvs(snapshot_csv, premium_csv)
    assert result.premium_candle_count == 1


def test_valid_csvs_return_symbols(tmp_path):
    snapshot_csv, premium_csv = _write_csvs(tmp_path)
    result = validate_option_market_data_csvs(snapshot_csv, premium_csv)
    assert SYMBOL in result.symbols


# ---------------------------------------------------------------------------
# Missing files
# ---------------------------------------------------------------------------

def test_missing_snapshot_file_returns_invalid(tmp_path):
    _, premium_csv = _write_csvs(tmp_path)
    result = validate_option_market_data_csvs(tmp_path / "missing.csv", premium_csv)
    assert result.is_valid is False
    assert any("snapshot CSV file not found" in e for e in result.errors)


def test_missing_premium_file_returns_invalid(tmp_path):
    snapshot_csv, _ = _write_csvs(tmp_path)
    result = validate_option_market_data_csvs(snapshot_csv, tmp_path / "missing.csv")
    assert result.is_valid is False
    assert any("premium CSV file not found" in e for e in result.errors)


def test_both_files_missing_returns_two_errors(tmp_path):
    result = validate_option_market_data_csvs(
        tmp_path / "a.csv", tmp_path / "b.csv"
    )
    assert result.is_valid is False
    assert len(result.errors) == 2


# ---------------------------------------------------------------------------
# Invalid / empty CSV content
# ---------------------------------------------------------------------------

def test_empty_snapshot_csv_returns_invalid(tmp_path):
    snapshot_csv, premium_csv = _write_csvs(tmp_path)
    snapshot_csv.write_text("", encoding="utf-8")  # overwrite with empty after recording
    result = validate_option_market_data_csvs(snapshot_csv, premium_csv)
    assert result.is_valid is False
    assert any("snapshot CSV" in e for e in result.errors)


def test_empty_premium_csv_returns_invalid(tmp_path):
    snapshot_csv, premium_csv = _write_csvs(tmp_path)
    premium_csv.write_text("", encoding="utf-8")  # overwrite with empty after recording
    result = validate_option_market_data_csvs(snapshot_csv, premium_csv)
    assert result.is_valid is False
    assert any("premium CSV" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

def test_result_is_dataclass_instance(tmp_path):
    snapshot_csv, premium_csv = _write_csvs(tmp_path)
    result = validate_option_market_data_csvs(snapshot_csv, premium_csv)
    assert isinstance(result, OptionMarketDataCsvValidationResult)


# ---------------------------------------------------------------------------
# Broker-agnostic guard
# ---------------------------------------------------------------------------

def test_no_fyers_in_validator_source():
    source_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "data_recording"
        / "option_market_data_csv_validator.py"
    )
    assert "fyers" not in source_path.read_text(encoding="utf-8").lower()
