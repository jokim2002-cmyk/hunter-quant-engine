r"""
Validate Option Market Data CSV Demo

Synthetic/demo only. Not live market data. Not a profitability claim.
No orders are placed. No broker code.

Validates previously recorded synthetic/demo CSV files offline using
validate_option_market_data_csvs. Does not replay or backtest.

Run the recording demo first to generate the CSV files:
    .\.venv\Scripts\python.exe examples\record_in_memory_option_market_data.py

Then run this validation demo:
    .\.venv\Scripts\python.exe examples\validate_option_market_data_csv.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_recording.option_market_data_csv_validator import (
    validate_option_market_data_csvs,
)

DEFAULT_SNAPSHOT_CSV = REPO_ROOT / "data" / "recorded" / "in_memory_demo" / "demo_snapshots.csv"
DEFAULT_PREMIUM_CSV = REPO_ROOT / "data" / "recorded" / "in_memory_demo" / "demo_premiums.csv"


def run_demo(snapshot_csv_path: Path, premium_csv_path: Path) -> int:
    """Validate recorded CSV files offline. Does not replay or backtest.

    Does not place orders. Not a profitability claim.
    """
    if not snapshot_csv_path.exists() or not premium_csv_path.exists():
        print("Hunter Quant Engine - CSV Validation Demo")
        print("------------------------------------------")
        print("Demo CSV files not found.")
        print("Run the recording demo first:")
        print(r"    .\.venv\Scripts\python.exe examples\record_in_memory_option_market_data.py")
        return 1

    result = validate_option_market_data_csvs(snapshot_csv_path, premium_csv_path)

    print("Hunter Quant Engine - CSV Validation Demo")
    print("------------------------------------------")

    if not result.is_valid:
        print("CSV validation failed.")
        for error in result.errors:
            print(f"  Error: {error}")
        print("No replay or backtest was run.")
        print("No orders placed.")
        return 1

    print("CSV validation passed.")
    print(f"  Snapshot count      : {result.snapshot_count}")
    print(f"  Premium candle count: {result.premium_candle_count}")
    print(f"  Symbols             : {', '.join(result.symbols)}")
    print("Synthetic/demo CSV validation only. Not live market data.")
    print("No orders placed. Not a profitability claim.")
    return 0


def main() -> int:
    return run_demo(DEFAULT_SNAPSHOT_CSV, DEFAULT_PREMIUM_CSV)


if __name__ == "__main__":
    raise SystemExit(main())
