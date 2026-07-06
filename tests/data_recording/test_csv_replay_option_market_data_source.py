"""Tests for CsvReplayOptionMarketDataSource."""

from datetime import datetime, date
from pathlib import Path

import pytest

from src.data_recording.csv_option_market_data_recorder import CsvOptionMarketDataRecorder
from src.data_recording.csv_replay_option_market_data_source import (
    CsvReplayOptionMarketDataSource,
)
from src.data_recording.option_market_data_poller import OptionMarketDataPoller
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SYMBOL = "NIFTY_REPLAY_24200CE"
STRIKE = 24200.0
EXPIRY = date(2026, 7, 31)
SNAP_TS = datetime(2026, 7, 6, 9, 15)
CANDLE_TS = datetime(2026, 7, 6, 9, 15)
UNDERLYING_PRICE = 24210.0
LTP = 120.0
CANDLE_CLOSE = 118.0


def _contract() -> OptionContract:
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=EXPIRY,
        strike_price=STRIKE,
        option_type=OptionType.CE,
        lot_size=75,
        symbol=SYMBOL,
    )


def _snapshot() -> OptionChainSnapshot:
    entry = OptionChainEntry(
        contract=_contract(),
        last_traded_price=LTP,
        bid_price=119.5,
        ask_price=120.5,
        volume=500,
        open_interest=10000,
    )
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=UNDERLYING_PRICE,
        timestamp=SNAP_TS,
        entries=(entry,),
    )


def _candle() -> OptionPremiumCandle:
    return OptionPremiumCandle(
        timestamp=CANDLE_TS,
        open=115.0,
        high=122.0,
        low=113.0,
        close=CANDLE_CLOSE,
        volume=200,
    )


def _write_csvs(tmp_path) -> tuple[Path, Path]:
    """Write synthetic snapshot and premium CSVs using the recorder."""
    snapshot_csv = tmp_path / "snapshots.csv"
    premium_csv = tmp_path / "premiums.csv"
    recorder = CsvOptionMarketDataRecorder(
        snapshot_csv_path=snapshot_csv,
        premium_csv_path=premium_csv,
    )
    recorder.record_snapshot(_snapshot(), snapshot_id="replay-001")
    recorder.record_premium_candles(SYMBOL, (_candle(),))
    return snapshot_csv, premium_csv


# ---------------------------------------------------------------------------
# Snapshot loading
# ---------------------------------------------------------------------------

def test_loads_snapshot_from_csv(tmp_path):
    snapshot_csv, _ = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(snapshot_csv_path=snapshot_csv)
    snap = source.get_option_chain_snapshot()
    assert snap.underlying_symbol == "NIFTY"
    assert snap.underlying_price == UNDERLYING_PRICE
    assert snap.timestamp == SNAP_TS


def test_loaded_snapshot_entry_values(tmp_path):
    snapshot_csv, _ = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(snapshot_csv_path=snapshot_csv)
    snap = source.get_option_chain_snapshot()
    assert len(snap.entries) == 1
    entry = snap.entries[0]
    assert entry.contract.symbol == SYMBOL
    assert entry.contract.strike_price == STRIKE
    assert entry.contract.option_type == OptionType.CE
    assert entry.last_traded_price == LTP


def test_raises_when_snapshot_csv_not_configured(tmp_path):
    source = CsvReplayOptionMarketDataSource()
    with pytest.raises(ValueError, match="snapshot_csv_path is required"):
        source.get_option_chain_snapshot()


# ---------------------------------------------------------------------------
# Premium candle loading
# ---------------------------------------------------------------------------

def test_loads_premium_candles_from_csv(tmp_path):
    _, premium_csv = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(premium_csv_path=premium_csv)
    result = source.get_option_premium_candles([SYMBOL])
    assert SYMBOL in result
    assert len(result[SYMBOL]) == 1
    assert result[SYMBOL][0].close == CANDLE_CLOSE
    assert result[SYMBOL][0].timestamp == CANDLE_TS


def test_raises_when_premium_csv_not_configured(tmp_path):
    source = CsvReplayOptionMarketDataSource()
    with pytest.raises(ValueError, match="premium_csv_path is required"):
        source.get_option_premium_candles([SYMBOL])


def test_raises_for_unknown_symbol(tmp_path):
    _, premium_csv = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(premium_csv_path=premium_csv)
    with pytest.raises(ValueError, match="option premium candles not found for symbol: UNKNOWN"):
        source.get_option_premium_candles(["UNKNOWN"])


def test_raises_for_empty_symbols(tmp_path):
    _, premium_csv = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(premium_csv_path=premium_csv)
    with pytest.raises(ValueError, match="option premium candle symbols are required"):
        source.get_option_premium_candles([])


def test_raises_for_blank_symbol(tmp_path):
    _, premium_csv = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(premium_csv_path=premium_csv)
    with pytest.raises(ValueError, match="option premium candle symbol is required"):
        source.get_option_premium_candles([""])


# ---------------------------------------------------------------------------
# Poller integration
# ---------------------------------------------------------------------------

def test_works_with_poller_poll_snapshot(tmp_path):
    snapshot_csv, _ = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(snapshot_csv_path=snapshot_csv)
    poller = OptionMarketDataPoller(source)
    result = poller.poll_snapshot()
    assert result.has_snapshot
    assert result.snapshot.underlying_symbol == "NIFTY"
    assert result.snapshot.underlying_price == UNDERLYING_PRICE


def test_works_with_poller_poll_premium_candles(tmp_path):
    _, premium_csv = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(premium_csv_path=premium_csv)
    poller = OptionMarketDataPoller(source)
    result = poller.poll_premium_candles([SYMBOL])
    assert result.has_premium_candles
    assert SYMBOL in result.premium_candles_by_symbol
    assert result.premium_candles_by_symbol[SYMBOL][0].close == CANDLE_CLOSE


def test_poller_poll_combines_snapshot_and_candles(tmp_path):
    snapshot_csv, premium_csv = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(
        snapshot_csv_path=snapshot_csv,
        premium_csv_path=premium_csv,
    )
    poller = OptionMarketDataPoller(source)
    result = poller.poll(premium_symbols=[SYMBOL])
    assert result.has_snapshot
    assert result.has_premium_candles


# ---------------------------------------------------------------------------
# CSV is loaded lazily (only once)
# ---------------------------------------------------------------------------

def test_snapshot_csv_loaded_once(tmp_path):
    snapshot_csv, _ = _write_csvs(tmp_path)
    source = CsvReplayOptionMarketDataSource(snapshot_csv_path=snapshot_csv)
    snap1 = source.get_option_chain_snapshot()
    snap2 = source.get_option_chain_snapshot()
    assert snap1 is snap2


# ---------------------------------------------------------------------------
# Broker-agnostic guard
# ---------------------------------------------------------------------------

def test_no_fyers_imports():
    source_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "data_recording"
        / "csv_replay_option_market_data_source.py"
    )
    text = source_path.read_text(encoding="utf-8").lower()
    assert "fyers" not in text
