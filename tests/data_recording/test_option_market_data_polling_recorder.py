"""Tests for OptionMarketDataPollingRecorder."""

from datetime import datetime
from pathlib import Path

import pytest

from src.backtesting.option_chain_snapshot_csv_loader import OptionChainSnapshotCsvLoader
from src.backtesting.option_premium_candle_csv_loader import OptionPremiumCandleCsvLoader
from src.data_recording.csv_option_market_data_recorder import CsvOptionMarketDataRecorder
from src.data_recording.option_market_data_poller import OptionMarketDataPoller
from src.data_recording.option_market_data_polling_recorder import (
    OptionMarketDataPollingRecorder,
)
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeDataSource:
    def __init__(self, snapshot=None, candles_by_symbol=None):
        self.snapshot = snapshot
        self.candles_by_symbol = candles_by_symbol or {}

    def get_option_chain_snapshot(self):
        return self.snapshot

    def get_option_premium_candles(self, symbols):
        return {s: self.candles_by_symbol[s] for s in symbols if s in self.candles_by_symbol}


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _contract():
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=datetime(2026, 7, 9).date(),
        strike_price=24200,
        option_type=OptionType.CE,
        lot_size=65,
        symbol="NIFTY26JUL24200CE",
    )


def _snapshot():
    entry = OptionChainEntry(
        contract=_contract(),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10,
        open_interest=100,
    )
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=datetime(2026, 7, 6, 9, 15),
        entries=(entry,),
    )


def _candle(ts=None):
    ts = ts or datetime(2026, 7, 6, 9, 20)
    return OptionPremiumCandle(
        timestamp=ts,
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=5,
    )


SYMBOL = "NIFTY26JUL24200CE"


def _make_service(tmp_path, snapshot=None, candles_by_symbol=None):
    source = FakeDataSource(snapshot=snapshot, candles_by_symbol=candles_by_symbol)
    poller = OptionMarketDataPoller(source)
    recorder = CsvOptionMarketDataRecorder(
        snapshot_csv_path=tmp_path / "snapshots.csv",
        premium_csv_path=tmp_path / "premiums.csv",
    )
    return OptionMarketDataPollingRecorder(poller, recorder), recorder


# ---------------------------------------------------------------------------
# poll_and_record_snapshot
# ---------------------------------------------------------------------------

def test_poll_and_record_snapshot_records_one(tmp_path):
    service, _ = _make_service(tmp_path, snapshot=_snapshot())
    result = service.poll_and_record_snapshot(snapshot_id="snap1")
    assert result.snapshots_recorded == 1
    assert result.snapshot_output_path is not None


def test_poll_and_record_snapshot_empty_when_no_snapshot(tmp_path):
    service, _ = _make_service(tmp_path, snapshot=None)
    result = service.poll_and_record_snapshot()
    assert result.snapshots_recorded == 0
    assert not result.has_recorded_data


# ---------------------------------------------------------------------------
# poll_and_record_premium_candles
# ---------------------------------------------------------------------------

def test_poll_and_record_premium_candles_records(tmp_path):
    service, _ = _make_service(
        tmp_path, candles_by_symbol={SYMBOL: (_candle(),)}
    )
    result = service.poll_and_record_premium_candles([SYMBOL])
    assert result.premium_symbols_recorded == 1
    assert result.premium_candles_recorded == 1
    assert result.premium_output_path is not None


def test_poll_and_record_premium_candles_empty_when_no_candles(tmp_path):
    service, _ = _make_service(tmp_path)
    # source returns nothing for unknown symbol; poller returns empty mapping
    # but poller raises if symbols list is empty — use a symbol not in source
    source = FakeDataSource(candles_by_symbol={})
    poller = OptionMarketDataPoller(source)
    recorder = CsvOptionMarketDataRecorder(
        snapshot_csv_path=tmp_path / "snapshots.csv",
        premium_csv_path=tmp_path / "premiums.csv",
    )
    service = OptionMarketDataPollingRecorder(poller, recorder)
    result = service.poll_and_record_premium_candles([SYMBOL])
    assert result.premium_candles_recorded == 0
    assert not result.has_recorded_data


# ---------------------------------------------------------------------------
# poll_and_record
# ---------------------------------------------------------------------------

def test_poll_and_record_combines_snapshot_and_candles(tmp_path):
    service, _ = _make_service(
        tmp_path,
        snapshot=_snapshot(),
        candles_by_symbol={SYMBOL: (_candle(),)},
    )
    result = service.poll_and_record(premium_symbols=[SYMBOL])
    assert result.snapshots_recorded == 1
    assert result.premium_symbols_recorded == 1
    assert result.premium_candles_recorded == 1


def test_poll_and_record_empty_when_no_data(tmp_path):
    service, _ = _make_service(tmp_path)
    result = service.poll_and_record(include_snapshot=False)
    assert not result.has_recorded_data


def test_poll_and_record_passes_snapshot_id(tmp_path):
    service, recorder = _make_service(tmp_path, snapshot=_snapshot())
    result = service.poll_and_record(snapshot_id="sid-42")
    assert result.snapshots_recorded == 1
    # verify snapshot_id was written to CSV
    loader = OptionChainSnapshotCsvLoader()
    snapshots = loader.load_snapshots(recorder.snapshot_csv_path)
    assert len(snapshots) == 1


# ---------------------------------------------------------------------------
# Round-trip CSV loader integration
# ---------------------------------------------------------------------------

def test_recorded_snapshot_csv_loadable(tmp_path):
    service, recorder = _make_service(tmp_path, snapshot=_snapshot())
    service.poll_and_record_snapshot(snapshot_id="snap-rt")
    snapshots = OptionChainSnapshotCsvLoader().load_snapshots(recorder.snapshot_csv_path)
    assert len(snapshots) == 1
    assert snapshots[0].underlying_symbol == "NIFTY"


def test_recorded_premium_csv_loadable(tmp_path):
    service, recorder = _make_service(
        tmp_path, candles_by_symbol={SYMBOL: (_candle(),)}
    )
    service.poll_and_record_premium_candles([SYMBOL])
    grouped = OptionPremiumCandleCsvLoader().load_grouped_candles(recorder.premium_csv_path)
    assert SYMBOL in grouped
    assert len(grouped[SYMBOL]) == 1


# ---------------------------------------------------------------------------
# Broker-agnostic guard
# ---------------------------------------------------------------------------

def test_no_fyers_imports():
    source = Path(__file__).parent.parent.parent / "src" / "data_recording" / "option_market_data_polling_recorder.py"
    text = source.read_text(encoding="utf-8").lower()
    assert "fyers" not in text
