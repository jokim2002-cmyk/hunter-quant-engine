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

## Poll-and-record workflow

The poll-and-record workflow connects a broker-agnostic data source to the CSV recorder through a single coordinating service.

```
OptionMarketDataSource
↓
OptionMarketDataPoller
↓
OptionMarketDataPollingRecorder
↓
CsvOptionMarketDataRecorder
↓
snapshot CSV + premium CSV
↓
offline option-buy backtest CLI
```

Key properties of this workflow:

- It is broker-agnostic. No broker SDK is imported by any layer in this chain.
- A future broker adapter can implement OptionMarketDataSource to feed real data into the poller without touching the recorder or the backtest CLI.
- OptionMarketDataPollingRecorder does not place orders. It only records market data to CSV files.
- It does not claim profitability. Recorded data is raw market observation only.
- It should be used for offline backtesting and paper observer preparation, not for live execution.
- Real recorded market data should not be committed to the repository.

### Synthetic/demo poll-and-record example

The example below is synthetic/demo only. It uses an in-memory fake source and should not be used as real market data.

```python
from pathlib import Path
from datetime import datetime, date

from src.data_recording.csv_option_market_data_recorder import CsvOptionMarketDataRecorder
from src.data_recording.option_market_data_poller import OptionMarketDataPoller
from src.data_recording.option_market_data_polling_recorder import OptionMarketDataPollingRecorder
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType


class DemoDataSource:
    """Fake in-memory source for demo/documentation purposes only."""

    def get_option_chain_snapshot(self):
        contract = OptionContract(
            underlying_symbol="NIFTY",
            expiry_date=date(2026, 7, 31),
            strike_price=24200,
            option_type=OptionType.CE,
            lot_size=75,
            symbol="NIFTY_DEMO_24200CE",
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

    def get_option_premium_candles(self, symbols):
        candle = OptionPremiumCandle(
            timestamp=datetime(2026, 7, 6, 9, 15),
            open=118.0,
            high=125.0,
            low=115.0,
            close=120.0,
            volume=200,
        )
        return {s: (candle,) for s in symbols}


poller = OptionMarketDataPoller(DemoDataSource())
recorder = CsvOptionMarketDataRecorder(
    snapshot_csv_path="data/recorded/demo_snapshots.csv",
    premium_csv_path="data/recorded/demo_premiums.csv",
)
service = OptionMarketDataPollingRecorder(poller, recorder)

result = service.poll_and_record(
    premium_symbols=["NIFTY_DEMO_24200CE"],
    include_snapshot=True,
    snapshot_id="demo-001",
)
print(result.snapshots_recorded)       # 1
print(result.premium_candles_recorded) # 1
```

## In-memory demo source

InMemoryOptionMarketDataSource is for tests and demos only. It is not real market data.

- It is broker-agnostic. It contains no broker SDK or API calls.
- It provides synthetic OptionChainSnapshot and OptionPremiumCandle data from memory.
- It plugs directly into OptionMarketDataPoller and OptionMarketDataPollingRecorder.
- It does not place orders.
- It is not a profitability claim.
- Use it in unit tests, integration tests, and documentation examples.

```python
from datetime import datetime, date

from src.data_recording.csv_option_market_data_recorder import CsvOptionMarketDataRecorder
from src.data_recording.in_memory_option_market_data_source import InMemoryOptionMarketDataSource
from src.data_recording.option_market_data_poller import OptionMarketDataPoller
from src.data_recording.option_market_data_polling_recorder import OptionMarketDataPollingRecorder
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType

# Synthetic snapshot — not real market data.
contract = OptionContract(
    underlying_symbol="NIFTY",
    expiry_date=date(2026, 7, 31),
    strike_price=24200,
    option_type=OptionType.CE,
    lot_size=75,
    symbol="NIFTY_DEMO_24200CE",
)
entry = OptionChainEntry(
    contract=contract,
    last_traded_price=120.0,
    bid_price=119.5,
    ask_price=120.5,
    volume=500,
    open_interest=10000,
)
snapshot = OptionChainSnapshot(
    underlying_symbol="NIFTY",
    underlying_price=24210.0,
    timestamp=datetime(2026, 7, 6, 9, 15),
    entries=(entry,),
)
candle = OptionPremiumCandle(
    timestamp=datetime(2026, 7, 6, 9, 15),
    open=118.0,
    high=125.0,
    low=115.0,
    close=120.0,
    volume=200,
)

source = InMemoryOptionMarketDataSource(
    snapshot=snapshot,
    premium_candles_by_symbol={"NIFTY_DEMO_24200CE": (candle,)},
)
poller = OptionMarketDataPoller(source)
recorder = CsvOptionMarketDataRecorder(
    snapshot_csv_path="data/recorded/demo_snapshots.csv",
    premium_csv_path="data/recorded/demo_premiums.csv",
)
service = OptionMarketDataPollingRecorder(poller, recorder)

result = service.poll_and_record(
    premium_symbols=["NIFTY_DEMO_24200CE"],
    include_snapshot=True,
    snapshot_id="demo-001",
)
print(result.snapshots_recorded)       # 1
print(result.premium_candles_recorded) # 1
```

## CSV replay source

CsvReplayOptionMarketDataSource replays previously recorded CSV data offline.

- It is broker-agnostic. It does not use FYERS or any broker SDK.
- It reads snapshot and premium candle CSV files written by CsvOptionMarketDataRecorder.
- It does not use live or real market data by itself.
- It does not place orders.
- It is not a profitability claim.
- It plugs into OptionMarketDataPoller using the same source interface.

## Offline in-memory recording demo

The demo script at `examples/record_in_memory_option_market_data.py` runs the full broker-agnostic recording chain using synthetic in-memory data only.

What it uses:

- InMemoryOptionMarketDataSource — synthetic data, not real market data
- OptionMarketDataPoller
- OptionMarketDataPollingRecorder
- CsvOptionMarketDataRecorder

What it does not do:

- It does not use FYERS or any broker SDK.
- It does not use real market data.
- It does not place orders.
- It is not a profitability claim.
- It is only a safe offline workflow demo.

Output is written to `data/recorded/in_memory_demo/` which is generated output and stays gitignored under `data/recorded/`.

Run on Windows PowerShell from the repository root:

```powershell
.\.venv\Scripts\python.exe examples\record_in_memory_option_market_data.py
```

Expected safe output:

- Snapshot CSV created at `data/recorded/in_memory_demo/demo_snapshots.csv`
- Premium CSV created at `data/recorded/in_memory_demo/demo_premiums.csv`
- Synthetic/demo summary printed to console
- No orders placed

## Offline CSV replay demo

The demo script at `examples/replay_csv_option_market_data.py` replays previously recorded synthetic/demo CSV files offline through CsvReplayOptionMarketDataSource and OptionMarketDataPoller.

- It validates CSV files before replay using `validate_option_market_data_csvs`.
- Invalid CSV files fail safely. No replay is run and no orders are placed if validation fails.
- It does not use FYERS or any broker SDK.
- It does not use live or real market data.
- It does not place orders.
- It is not a profitability claim.

First run the recording demo to generate the CSV files:

```powershell
.\.venv\Scripts\python.exe examples\record_in_memory_option_market_data.py
```

Then run the replay demo:

```powershell
.\.venv\Scripts\python.exe examples\replay_csv_option_market_data.py
```

## Safe record-to-replay workflow

This is a beginner-friendly offline workflow check using synthetic/demo data only.

Step 1 — Run the in-memory recording demo to generate synthetic CSV files:

```powershell
.\.venv\Scripts\python.exe examples\record_in_memory_option_market_data.py
```

This creates synthetic demo CSV files under `data/recorded/in_memory_demo/`.

Step 2 — Run the CSV replay demo to replay those files offline:

```powershell
.\.venv\Scripts\python.exe examples\replay_csv_option_market_data.py
```

The replay step uses CsvReplayOptionMarketDataSource and OptionMarketDataPoller to read the CSV files written in Step 1.

Properties of this workflow:

- It is broker-agnostic. It does not use FYERS or any broker SDK.
- It does not use live or real market data.
- It does not place orders.
- It is not a profitability claim.
- It is only a safe local workflow check using synthetic/demo data.

## Recorded CSV validation

`validate_option_market_data_csvs` checks recorded CSV files before replay or backtest usage.

- It is offline and broker-agnostic. It does not use FYERS or any broker SDK.
- It does not use live or real market data.
- It does not place orders.
- It is not a profitability claim.
- It returns an `OptionMarketDataCsvValidationResult` with `is_valid`, `errors`, `snapshot_count`, `premium_candle_count`, and `symbols`.
- Errors are returned as messages instead of raising, so callers can decide how to handle them.

## Offline CSV validation demo

The demo script at `examples/validate_option_market_data_csv.py` validates recorded synthetic/demo CSV files offline without replaying them.

- It does not use FYERS or any broker SDK.
- It does not use live or real market data.
- It does not place orders.
- It is not a profitability claim.

First generate demo CSV files:

```powershell
.\.venv\Scripts\python.exe examples\record_in_memory_option_market_data.py
```

Then validate:

```powershell
.\.venv\Scripts\python.exe examples\validate_option_market_data_csv.py
```

## Notes

- This layer is broker-agnostic.
- It is for offline backtesting and preparing paper/live observer workflows.
- It is not a profitability claim.
- It does not place orders.
- It should not contain secrets, credentials, or broker-specific implementation details.
