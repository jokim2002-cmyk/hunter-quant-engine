"""End-to-end smoke test: in-memory source → poll-and-record → CSV loaders."""

from datetime import datetime, date

from src.backtesting.option_chain_snapshot_csv_loader import OptionChainSnapshotCsvLoader
from src.backtesting.option_premium_candle_csv_loader import OptionPremiumCandleCsvLoader
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
# Synthetic data constants
# ---------------------------------------------------------------------------

SYMBOL = "NIFTY_SMOKE_24200CE"
STRIKE = 24200.0
EXPIRY = date(2026, 7, 31)
SNAP_TS = datetime(2026, 7, 6, 9, 15)
CANDLE_TS = datetime(2026, 7, 6, 9, 15)
UNDERLYING_PRICE = 24210.0
LTP = 120.0
CANDLE_CLOSE = 118.0


def _build_snapshot() -> OptionChainSnapshot:
    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=EXPIRY,
        strike_price=STRIKE,
        option_type=OptionType.CE,
        lot_size=75,
        symbol=SYMBOL,
    )
    entry = OptionChainEntry(
        contract=contract,
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


def _build_candle() -> OptionPremiumCandle:
    return OptionPremiumCandle(
        timestamp=CANDLE_TS,
        open=115.0,
        high=122.0,
        low=113.0,
        close=CANDLE_CLOSE,
        volume=200,
    )


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def test_in_memory_recording_end_to_end(tmp_path):
    snapshot_csv = tmp_path / "smoke_snapshots.csv"
    premium_csv = tmp_path / "smoke_premiums.csv"

    # Build the chain.
    source = InMemoryOptionMarketDataSource(
        snapshot=_build_snapshot(),
        premium_candles_by_symbol={SYMBOL: (_build_candle(),)},
    )
    poller = OptionMarketDataPoller(source)
    recorder = CsvOptionMarketDataRecorder(
        snapshot_csv_path=snapshot_csv,
        premium_csv_path=premium_csv,
    )
    service = OptionMarketDataPollingRecorder(poller, recorder)

    # Execute.
    result = service.poll_and_record(
        premium_symbols=[SYMBOL],
        include_snapshot=True,
        snapshot_id="smoke-001",
    )

    # --- recording result assertions ---
    assert result.snapshots_recorded == 1
    assert result.premium_symbols_recorded == 1
    assert result.premium_candles_recorded == 1

    # --- CSV files exist ---
    assert snapshot_csv.exists()
    assert premium_csv.exists()

    # --- snapshot round-trip ---
    snapshots = OptionChainSnapshotCsvLoader().load_snapshots(snapshot_csv)
    assert len(snapshots) == 1
    loaded_snap = snapshots[0]
    assert loaded_snap.underlying_symbol == "NIFTY"
    assert loaded_snap.underlying_price == UNDERLYING_PRICE
    assert loaded_snap.timestamp == SNAP_TS
    assert len(loaded_snap.entries) == 1
    loaded_entry = loaded_snap.entries[0]
    assert loaded_entry.contract.symbol == SYMBOL
    assert loaded_entry.contract.strike_price == STRIKE
    assert loaded_entry.contract.option_type == OptionType.CE
    assert loaded_entry.contract.expiry_date == EXPIRY
    assert loaded_entry.last_traded_price == LTP

    # --- premium candle round-trip ---
    grouped = OptionPremiumCandleCsvLoader().load_grouped_candles(premium_csv)
    assert SYMBOL in grouped
    loaded_candles = grouped[SYMBOL]
    assert len(loaded_candles) == 1
    loaded_candle = loaded_candles[0]
    assert loaded_candle.timestamp == CANDLE_TS
    assert loaded_candle.close == CANDLE_CLOSE
