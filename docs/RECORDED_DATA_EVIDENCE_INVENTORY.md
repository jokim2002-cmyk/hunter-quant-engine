# HQE Recorded Data Evidence Inventory

The recorded-data evidence inventory is the first step of the real evidence
pipeline after the v0.2 live-readiness scaffold checkpoint.

It scans local recorded/historical data folders and writes an inventory report.

It is not live trading.

It does not use broker APIs.
It does not use live market data.
It does not place real orders.
It does not claim profitability.

## Command

Run:

    .\hqe_recorded_data_inventory.bat

The command scans:

    data\recorded
    data\live_recording

Supported file types:

- `.csv`
- `.json`
- `.jsonl`
- `.parquet`

The command writes:

    reports\paper_trading\recorded_data_inventory\inventory.json
    reports\paper_trading\recorded_data_inventory\inventory.txt
    reports\paper_trading\recorded_data_inventory\manifest.json

## Meaning of Pass

A pass means:

    supported recorded data files were found and none were empty

A pass does not mean:

- the strategy is profitable
- the data is complete enough for live trading
- broker execution is enabled
- real orders are enabled

## Next Phase

After this inventory passes, the next evidence module can parse discovered
records into a normalized replay dataset for paper backtesting.
