# Option Market Data Recording

This recorder is broker-agnostic. It is designed to capture option market data in a simple CSV form that can be reused by offline backtesting and paper/live observer preparation without coupling the recording logic to any one broker.

The recorder writes:
- option chain snapshots
- option premium candles

It is intended for offline analysis and local experimentation. It does not place orders, does not claim profitability, and does not contain broker credentials.

Future broker adapters such as FYERS may feed this layer, but adapter code should stay outside the core recording logic.

## Workflow

Broker/API adapter
↓
OptionChainSnapshot + OptionPremiumCandle
↓
CsvOptionMarketDataRecorder
↓
snapshot CSV + premium CSV
↓
CSV loaders
↓
offline option-buy backtest CLI

## Synthetic/demo usage example

The examples below are synthetic/demo only and should not be used as real market data.

```python
from pathlib import Path

from src.data_recording.csv_option_market_data_recorder import (
    CsvOptionMarketDataRecorder,
)

snapshot_csv = Path("data/recorded/demo_snapshots.csv")
premium_csv = Path("data/recorded/demo_premium.csv")
recorder = CsvOptionMarketDataRecorder(snapshot_csv, premium_csv)

# Record one snapshot.
recorder.record_snapshot(snapshot)

# Record premium candles for one symbol.
recorder.record_premium_candles("NIFTY_DEMO_24200CE", candles)

# Record a batch of snapshots and candles.
recorder.record_batch(
    snapshots=(snapshot_a, snapshot_b),
    premium_candles_by_symbol={
        "NIFTY_DEMO_24200CE": (candle_one, candle_two),
    },
)
```

## Output paths and storage guidance

Use output paths such as:
- data/recorded/demo_snapshots.csv
- data/recorded/demo_premium.csv

Avoid committing real recorded market data. Generated data should stay ignored unless you intentionally create tiny fixtures for tests or documentation.

## Notes

- This layer is broker-agnostic.
- It is for offline backtesting and preparing paper/live observer workflows.
- It is not a profitability claim.
- It does not place orders.
- It should not contain secrets, credentials, or broker-specific implementation details.
