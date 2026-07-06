"""
Record In-Memory Option Market Data Demo

Synthetic/demo only. Not real market data. Not a profitability claim.
No orders are placed. No broker code.

Generates synthetic option chain snapshot and premium candle data using
InMemoryOptionMarketDataSource, records it through the broker-agnostic
recording chain, and writes CSV files to a local output directory.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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

DEMO_SYMBOL = "NIFTY_DEMO_24200CE"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "recorded" / "in_memory_demo"


def _build_snapshot() -> OptionChainSnapshot:
    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 31),
        strike_price=24200,
        option_type=OptionType.CE,
        lot_size=75,
        symbol=DEMO_SYMBOL,
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


def _build_candle() -> OptionPremiumCandle:
    return OptionPremiumCandle(
        timestamp=datetime(2026, 7, 6, 9, 15),
        open=118.0,
        high=125.0,
        low=115.0,
        close=120.0,
        volume=200,
    )


def run_demo(output_dir: Path) -> int:
    """Run the in-memory recording demo and write CSV files to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_csv = output_dir / "demo_snapshots.csv"
    premium_csv = output_dir / "demo_premiums.csv"

    source = InMemoryOptionMarketDataSource(
        snapshot=_build_snapshot(),
        premium_candles_by_symbol={DEMO_SYMBOL: (_build_candle(),)},
    )
    poller = OptionMarketDataPoller(source)
    recorder = CsvOptionMarketDataRecorder(
        snapshot_csv_path=snapshot_csv,
        premium_csv_path=premium_csv,
    )
    service = OptionMarketDataPollingRecorder(poller, recorder)

    result = service.poll_and_record(
        premium_symbols=[DEMO_SYMBOL],
        include_snapshot=True,
        snapshot_id="demo-001",
    )

    print("Hunter Quant Engine - In-Memory Option Market Data Recording Demo")
    print("------------------------------------------------------------------")
    print("SYNTHETIC DEMO DATA ONLY. Not real market data.")
    print("No orders placed. Not a profitability claim.")
    print(f"Snapshots recorded      : {result.snapshots_recorded}")
    print(f"Premium candles recorded: {result.premium_candles_recorded}")
    print(f"Snapshot CSV : {snapshot_csv}")
    print(f"Premium CSV  : {premium_csv}")
    return 0


def main() -> int:
    return run_demo(DEFAULT_OUTPUT_DIR)


if __name__ == "__main__":
    raise SystemExit(main())
