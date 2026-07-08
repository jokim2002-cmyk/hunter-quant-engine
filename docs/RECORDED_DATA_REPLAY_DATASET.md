# Recorded Data Replay Dataset

Module O adds a paper/simulation-only replay dataset normalizer for recorded data evidence.

Purpose:
The normalizer converts discovered recorded market-data files into a simple replay dataset scaffold. It is intentionally conservative and does not assume a final broker/vendor file format yet.

Safety boundary:
This module is paper/evidence only.

It does not:
- connect to a broker
- request live market data
- place real orders
- use real money
- prove profitability

This report is not a profitability claim.

Default inventory input:
reports\paper_trading\recorded_data_inventory\inventory.json

Default discovery roots:
data\recorded
data\live_recording

Supported discovery file types:
- .csv
- .json
- .jsonl
- .parquet

CSV, JSON, and JSONL receive simple parsing. Parquet is discovered but parsing is intentionally deferred in this scaffold.

Normalized replay fields:
- timestamp
- open
- high
- low
- close
- volume

Common aliases like time, datetime, o, h, l, c, price, and vol are handled.

Command:
.\scripts\paper_trading\hqe_recorded_data_replay_dataset.bat

Optional custom path example:
.\scripts\paper_trading\hqe_recorded_data_replay_dataset.bat --recorded-root data\recorded --output-dir reports\paper_trading\recorded_data_replay_dataset

Default output folder:
reports\paper_trading\recorded_data_replay_dataset

Generated files:
- dataset.json
- dataset.jsonl
- dataset.txt
- manifest.json

Generated reports/data remain ignored and must not be committed.
