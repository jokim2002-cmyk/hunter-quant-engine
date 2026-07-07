# Recorded Data Replay Quality Gate

Module P adds a paper/simulation-only quality gate for normalized recorded-data replay datasets.

Purpose:
The quality gate audits the replay dataset created by Module O before later evidence modules use it.

Default input:
reports\paper_trading\recorded_data_replay_dataset\dataset.json

Default output folder:
reports\paper_trading\recorded_data_replay_quality_gate

Generated files:
- quality_gate.json
- quality_gate.txt
- manifest.json

Checks:
- dataset exists and is valid JSON
- normalized records exist
- required timestamp/open/high/low/close fields are present
- OHLC values are structurally sane
- volume is not negative
- duplicate source/timestamp/row records are flagged
- out-of-order parseable timestamps are flagged
- source parse errors and skipped rows are surfaced

Command:
.\hqe_recorded_data_replay_quality_gate.bat

Optional custom path example:
.\hqe_recorded_data_replay_quality_gate.bat --dataset reports\paper_trading\recorded_data_replay_dataset\dataset.json --output-dir reports\paper_trading\recorded_data_replay_quality_gate

Safety boundary:
This module is paper/evidence only. It does not connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
