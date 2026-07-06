"""Tests for InMemoryOptionMarketDataSource."""

from datetime import datetime, date
from pathlib import Path

import pytest

from src.data_recording.csv_option_market_data_recorder import CsvOptionMarketDataRecorder
from src.data_recording.in_memory_option_market_data_source import (
    InMemoryOptionMarketDataSource,
)
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
# Helpers
# ---------------------------------------------------------------------------

def _candle(timestamp: datetime) -> OptionPremiumCandle:
    return OptionPremiumCandle(
        timestamp=timestamp,
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=10,
    )


def _contract(symbol: str, option_type: OptionType, strike: float) -> OptionContract:
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 31),
        strike_price=strike,
        option_type=option_type,
        lot_size=75,
        symbol=symbol,
    )


def _entry(symbol: str, option_type: OptionType, strike: float) -> OptionChainEntry:
    return OptionChainEntry(
        contract=_contract(symbol, option_type, strike),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=500,
        open_interest=10000,
    )


def _snapshot(
    timestamp: datetime,
    entries: tuple[OptionChainEntry, ...],
) -> OptionChainSnapshot:
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24200.0,
        timestamp=timestamp,
        entries=entries,
    )


SYMBOL = "NIFTY_DEMO_24200CE"
TS = datetime(2026, 7, 6, 9, 15)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

def test_returns_configured_snapshot():
    snap = _snapshot(TS, (_entry(SYMBOL, OptionType.CE, 24200),))
    source = InMemoryOptionMarketDataSource(snapshot=snap)
    assert source.get_option_chain_snapshot() is snap


def test_raises_when_snapshot_missing():
    source = InMemoryOptionMarketDataSource()
    with pytest.raises(ValueError, match="option chain snapshot is not available"):
        source.get_option_chain_snapshot()


# ---------------------------------------------------------------------------
# Premium candles
# ---------------------------------------------------------------------------

def test_returns_requested_premium_candles():
    candles = (_candle(TS),)
    source = InMemoryOptionMarketDataSource(
        premium_candles_by_symbol={SYMBOL: candles}
    )
    result = source.get_option_premium_candles([SYMBOL])
    assert SYMBOL in result
    assert result[SYMBOL] == candles


def test_returns_only_requested_symbols():
    sym_a = "NIFTY_DEMO_24200CE"
    sym_b = "NIFTY_DEMO_24300PE"
    source = InMemoryOptionMarketDataSource(
        premium_candles_by_symbol={
            sym_a: (_candle(TS),),
            sym_b: (_candle(TS),),
        }
    )
    result = source.get_option_premium_candles([sym_a])
    assert sym_a in result
    assert sym_b not in result


def test_sorts_premium_candles_by_timestamp():
    t1 = datetime(2026, 7, 6, 9, 20)
    t2 = datetime(2026, 7, 6, 9, 15)
    source = InMemoryOptionMarketDataSource(
        premium_candles_by_symbol={SYMBOL: (_candle(t1), _candle(t2))}
    )
    result = source.get_option_premium_candles([SYMBOL])
    timestamps = [c.timestamp for c in result[SYMBOL]]
    assert timestamps == sorted(timestamps)


def test_normalizes_premium_candles_to_tuples():
    source = InMemoryOptionMarketDataSource(
        premium_candles_by_symbol={SYMBOL: [_candle(TS)]}
    )
    result = source.get_option_premium_candles([SYMBOL])
    assert isinstance(result[SYMBOL], tuple)


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

def test_rejects_blank_symbol_key_in_constructor():
    with pytest.raises(ValueError, match="option premium candle symbol is required"):
        InMemoryOptionMarketDataSource(
            premium_candles_by_symbol={"": (_candle(TS),)}
        )


def test_rejects_empty_candle_sequence_in_constructor():
    with pytest.raises(
        ValueError,
        match=f"option premium candles are required for symbol: {SYMBOL}",
    ):
        InMemoryOptionMarketDataSource(
            premium_candles_by_symbol={SYMBOL: ()}
        )


# ---------------------------------------------------------------------------
# get_option_premium_candles validation
# ---------------------------------------------------------------------------

def test_rejects_empty_requested_symbols():
    source = InMemoryOptionMarketDataSource(
        premium_candles_by_symbol={SYMBOL: (_candle(TS),)}
    )
    with pytest.raises(ValueError, match="option premium candle symbols are required"):
        source.get_option_premium_candles([])


def test_rejects_blank_requested_symbol():
    source = InMemoryOptionMarketDataSource(
        premium_candles_by_symbol={SYMBOL: (_candle(TS),)}
    )
    with pytest.raises(ValueError, match="option premium candle symbol is required"):
        source.get_option_premium_candles([""])


def test_rejects_unknown_requested_symbol():
    source = InMemoryOptionMarketDataSource(
        premium_candles_by_symbol={SYMBOL: (_candle(TS),)}
    )
    with pytest.raises(
        ValueError,
        match="option premium candles not found for symbol: UNKNOWN",
    ):
        source.get_option_premium_candles(["UNKNOWN"])


# ---------------------------------------------------------------------------
# available_symbols
# ---------------------------------------------------------------------------

def test_available_symbols_returns_sorted():
    sym_b = "NIFTY_DEMO_24300PE"
    sym_a = "NIFTY_DEMO_24200CE"
    source = InMemoryOptionMarketDataSource(
        premium_candles_by_symbol={
            sym_b: (_candle(TS),),
            sym_a: (_candle(TS),),
        }
    )
    assert source.available_symbols == (sym_a, sym_b)


# ---------------------------------------------------------------------------
# Poller integration
# ---------------------------------------------------------------------------

def test_works_with_poller_poll_snapshot():
    snap = _snapshot(TS, (_entry(SYMBOL, OptionType.CE, 24200),))
    source = InMemoryOptionMarketDataSource(snapshot=snap)
    poller = OptionMarketDataPoller(source)
    result = poller.poll_snapshot()
    assert result.has_snapshot
    assert result.snapshot is snap


def test_works_with_poller_poll_premium_candles():
    candles = (_candle(TS),)
    source = InMemoryOptionMarketDataSource(
        premium_candles_by_symbol={SYMBOL: candles}
    )
    poller = OptionMarketDataPoller(source)
    result = poller.poll_premium_candles([SYMBOL])
    assert result.has_premium_candles
    assert result.premium_candles_by_symbol[SYMBOL] == candles


# ---------------------------------------------------------------------------
# PollingRecorder integration
# ---------------------------------------------------------------------------

def test_works_with_polling_recorder(tmp_path):
    snap = _snapshot(TS, (_entry(SYMBOL, OptionType.CE, 24200),))
    candles = (_candle(TS),)
    source = InMemoryOptionMarketDataSource(
        snapshot=snap,
        premium_candles_by_symbol={SYMBOL: candles},
    )
    poller = OptionMarketDataPoller(source)
    recorder = CsvOptionMarketDataRecorder(
        snapshot_csv_path=tmp_path / "snapshots.csv",
        premium_csv_path=tmp_path / "premiums.csv",
    )
    service = OptionMarketDataPollingRecorder(poller, recorder)

    result = service.poll_and_record(
        premium_symbols=[SYMBOL],
        include_snapshot=True,
        snapshot_id="test-001",
    )

    assert result.snapshots_recorded == 1
    assert result.premium_symbols_recorded == 1
    assert result.premium_candles_recorded == 1


# ---------------------------------------------------------------------------
# Broker-agnostic guard
# ---------------------------------------------------------------------------

def test_no_fyers_imports():
    source_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "data_recording"
        / "in_memory_option_market_data_source.py"
    )
    text = source_path.read_text(encoding="utf-8").lower()
    assert "fyers" not in text
