# Recorded Data Replay Dry-Run

Module Q adds a paper/simulation-only dry-run player for normalized recorded-data replay datasets.

Purpose:
The dry-run player converts normalized replay records into a deterministic event stream. This helps prove the dataset can be consumed by later paper evidence modules before any strategy integration.

Default input dataset:
reports\paper_trading\recorded_data_replay_dataset\dataset.json

Default quality gate input:
reports\paper_trading\recorded_data_replay_quality_gate\quality_gate.json

Default output folder:
reports\paper_trading\recorded_data_replay_dry_run

Generated files:
- dry_run_report.json
- dry_run_events.jsonl
- dry_run_report.txt
- manifest.json

Command:
.\hqe_recorded_data_replay_dry_run.bat

Optional custom path example:
.\hqe_recorded_data_replay_dry_run.bat --dataset reports\paper_trading\recorded_data_replay_dataset\dataset.json --quality-gate reports\paper_trading\recorded_data_replay_quality_gate\quality_gate.json --output-dir reports\paper_trading\recorded_data_replay_dry_run

Optional record limit:
.\hqe_recorded_data_replay_dry_run.bat --max-records 100

Safety boundary:
This module is paper/evidence only. It does not run strategies, create trade plans, connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
