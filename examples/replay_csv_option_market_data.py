r"""
Replay CSV Option Market Data Demo

Synthetic/demo only. Not live market data. Not a profitability claim.
No orders are placed. No broker code.

Replays previously recorded synthetic/demo CSV files through
CsvReplayOptionMarketDataSource and OptionMarketDataPoller offline.

CSV files are validated before replay. Invalid files fail safely.
No replay is run and no orders are placed if validation fails.

Run the recording demo first to generate the CSV files:
    .\.venv\Scripts\python.exe examples\record_in_memory_option_market_data.py

Then run this replay demo:
    .\.venv\Scripts\python.exe examples\replay_csv_option_market_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_recording.csv_replay_option_market_data_source import (
    CsvReplayOptionMarketDataSource,
)
from src.data_recording.option_market_data_csv_validator import (
    validate_option_market_data_csvs,
)
from src.data_recording.option_market_data_poller import OptionMarketDataPoller

DEMO_SYMBOL = "NIFTY_DEMO_24200CE"
DEFAULT_SNAPSHOT_CSV = REPO_ROOT / "data" / "recorded" / "in_memory_demo" / "demo_snapshots.csv"
DEFAULT_PREMIUM_CSV = REPO_ROOT / "data" / "recorded" / "in_memory_demo" / "demo_premiums.csv"


def run_demo(snapshot_csv_path: Path, premium_csv_path: Path) -> int:
    """Replay recorded CSV files through the broker-agnostic poller.

    Validates CSV files before replay. Fails safely if validation fails.
    Does not place orders. Not a profitability claim.
    """
    if not snapshot_csv_path.exists() or not premium_csv_path.exists():
        print("Hunter Quant Engine - CSV Replay Demo")
        print("--------------------------------------")
        print("Demo CSV files not found.")
        print("Run the recording demo first:")
        print(r"    .\.venv\Scripts\python.exe examples\record_in_memory_option_market_data.py")
        return 1

    validation_result = validate_option_market_data_csvs(snapshot_csv_path, premium_csv_path)

    if not validation_result.is_valid:
        print("Hunter Quant Engine - CSV Replay Demo")
        print("--------------------------------------")
        print("CSV validation failed.")
        for error in validation_result.errors:
            print(f"  Error: {error}")
        print("No replay was run.")
        print("No orders placed.")
        return 1

    print("Hunter Quant Engine - CSV Replay Demo")
    print("--------------------------------------")
    print("Validation passed.")
    print(f"  Snapshot count      : {validation_result.snapshot_count}")
    print(f"  Premium candle count: {validation_result.premium_candle_count}")
    print(f"  Symbols             : {', '.join(validation_result.symbols)}")

    source = CsvReplayOptionMarketDataSource(
        snapshot_csv_path=snapshot_csv_path,
        premium_csv_path=premium_csv_path,
    )
    poller = OptionMarketDataPoller(source)

    snapshot_result = poller.poll_snapshot()
    premium_result = poller.poll_premium_candles([DEMO_SYMBOL])

    snap = snapshot_result.snapshot
    candles = premium_result.premium_candles_by_symbol.get(DEMO_SYMBOL, ())

    print("CSV replay source used. Synthetic/demo CSV only.")
    print("Not live market data. No orders placed. Not a profitability claim.")
    print(f"Snapshot loaded         : {snap.underlying_symbol} @ {snap.underlying_price}")
    print(f"Snapshot timestamp      : {snap.timestamp}")
    print(f"Snapshot entries        : {len(snap.entries)}")
    print(f"Premium candles loaded  : {len(candles)} for {DEMO_SYMBOL}")
    print(f"Snapshot CSV : {snapshot_csv_path}")
    print(f"Premium CSV  : {premium_csv_path}")
    return 0


def main() -> int:
    return run_demo(DEFAULT_SNAPSHOT_CSV, DEFAULT_PREMIUM_CSV)


if __name__ == "__main__":
    raise SystemExit(main())
