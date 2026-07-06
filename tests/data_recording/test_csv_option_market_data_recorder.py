"""Tests for the CSV option market data recorder."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from src.backtesting.option_chain_snapshot_csv_loader import (
    OptionChainSnapshotCsvLoader,
)
from src.backtesting.option_premium_candle_csv_loader import (
    OptionPremiumCandleCsvLoader,
)
from src.data_recording.csv_option_market_data_recorder import (
    CsvOptionMarketDataRecorder,
)
from src.data_recording.option_market_data_recording_result import (
    OptionMarketDataRecordingResult,
)
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType


def _candle(timestamp: datetime) -> OptionPremiumCandle:
    return OptionPremiumCandle(
        timestamp=timestamp,
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=10,
    )


def _contract(symbol: str, option_type: OptionType, strike: float) -> OptionContract:
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=strike,
        option_type=option_type,
        lot_size=65,
        symbol=symbol,
    )


def _entry(symbol: str, option_type: OptionType, strike: float) -> OptionChainEntry:
    return OptionChainEntry(
        contract=_contract(symbol, option_type, strike),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=1000,
        open_interest=5000,
    )


def _snapshot(timestamp: datetime, entries: tuple[OptionChainEntry, ...]) -> OptionChainSnapshot:
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=timestamp,
        entries=entries,
    )


def test_recording_result_validates_non_negative_counts():
    with pytest.raises(ValueError):
        OptionMarketDataRecordingResult(snapshots_recorded=-1)


def test_recording_result_has_recorded_data_is_false_when_empty():
    result = OptionMarketDataRecordingResult()

    assert result.has_recorded_data is False


def test_recording_result_has_recorded_data_is_true_when_snapshots_recorded():
    result = OptionMarketDataRecordingResult(snapshots_recorded=1)

    assert result.has_recorded_data is True


def test_recording_result_has_recorded_data_is_true_when_premium_candles_recorded():
    result = OptionMarketDataRecordingResult(premium_candles_recorded=1)

    assert result.has_recorded_data is True


def test_recorder_creates_snapshot_csv_when_recording_snapshot(tmp_path):
    snapshot_path = tmp_path / "snapshots.csv"
    premium_path = tmp_path / "premium.csv"
    recorder = CsvOptionMarketDataRecorder(snapshot_path, premium_path)
    snapshot = _snapshot(datetime(2026, 7, 6, 9, 15), (_entry("SYM1", OptionType.CE, 24200.0),))

    result = recorder.record_snapshot(snapshot, snapshot_id="demo-snapshot")

    assert result.snapshots_recorded == 1
    assert snapshot_path.exists()
    assert result.snapshot_output_path == str(snapshot_path)


def test_recorder_creates_premium_csv_when_recording_premium_candles(tmp_path):
    snapshot_path = tmp_path / "snapshots.csv"
    premium_path = tmp_path / "premium.csv"
    recorder = CsvOptionMarketDataRecorder(snapshot_path, premium_path)

    result = recorder.record_premium_candles("SYM1", (_candle(datetime(2026, 7, 6, 9, 15)),))

    assert result.premium_symbols_recorded == 1
    assert result.premium_candles_recorded == 1
    assert premium_path.exists()
    assert result.premium_output_path == str(premium_path)


def test_record_batch_records_multiple_snapshots(tmp_path):
    snapshot_path = tmp_path / "snapshots.csv"
    premium_path = tmp_path / "premium.csv"
    recorder = CsvOptionMarketDataRecorder(snapshot_path, premium_path)
    snapshots = (
        _snapshot(datetime(2026, 7, 6, 9, 15), (_entry("SYM1", OptionType.CE, 24200.0),)),
        _snapshot(datetime(2026, 7, 6, 9, 30), (_entry("SYM2", OptionType.PE, 24200.0),)),
    )

    result = recorder.record_batch(snapshots=snapshots)

    assert result.snapshots_recorded == 2
    assert snapshot_path.exists()


def test_record_batch_records_premium_candles_for_multiple_symbols(tmp_path):
    snapshot_path = tmp_path / "snapshots.csv"
    premium_path = tmp_path / "premium.csv"
    recorder = CsvOptionMarketDataRecorder(snapshot_path, premium_path)
    candles_by_symbol = {
        "SYM1": (_candle(datetime(2026, 7, 6, 9, 15)),),
        "SYM2": (_candle(datetime(2026, 7, 6, 9, 30)),),
    }

    result = recorder.record_batch(premium_candles_by_symbol=candles_by_symbol)

    assert result.premium_symbols_recorded == 2
    assert result.premium_candles_recorded == 2
    assert premium_path.exists()


def test_record_batch_returns_zero_counts_when_empty(tmp_path):
    snapshot_path = tmp_path / "snapshots.csv"
    premium_path = tmp_path / "premium.csv"
    recorder = CsvOptionMarketDataRecorder(snapshot_path, premium_path)

    result = recorder.record_batch()

    assert result.snapshots_recorded == 0
    assert result.premium_symbols_recorded == 0
    assert result.premium_candles_recorded == 0
    assert result.has_recorded_data is False


def test_recorded_snapshot_csv_can_be_loaded_by_loader(tmp_path):
    snapshot_path = tmp_path / "snapshots.csv"
    premium_path = tmp_path / "premium.csv"
    recorder = CsvOptionMarketDataRecorder(snapshot_path, premium_path)
    snapshot = _snapshot(datetime(2026, 7, 6, 9, 15), (_entry("SYM1", OptionType.CE, 24200.0),))

    recorder.record_snapshot(snapshot)
    snapshots = OptionChainSnapshotCsvLoader().load_snapshots(snapshot_path)

    assert len(snapshots) == 1
    assert snapshots[0].entries[0].contract.symbol == "SYM1"


def test_recorded_premium_csv_can_be_loaded_by_loader(tmp_path):
    snapshot_path = tmp_path / "snapshots.csv"
    premium_path = tmp_path / "premium.csv"
    recorder = CsvOptionMarketDataRecorder(snapshot_path, premium_path)

    recorder.record_premium_candles("SYM1", (_candle(datetime(2026, 7, 6, 9, 15)),))
    grouped = OptionPremiumCandleCsvLoader().load_grouped_candles(premium_path)

    assert list(grouped) == ["SYM1"]
    assert len(grouped["SYM1"]) == 1


def test_recorder_remains_broker_agnostic_and_does_not_import_fyers_modules():
    recorder_path = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "data_recording"
        / "csv_option_market_data_recorder.py"
    )
    source = recorder_path.read_text(encoding="utf-8")

    assert "fyers" not in source.lower()
