# Recorded Data Replay Readiness Gate

Module T adds a one-command paper/simulation-only readiness gate for recorded-data replay evidence.

Purpose:
The readiness gate runs:
1. Recorded data replay evidence bundle.
2. Recorded data replay acceptance gate.
3. Final readiness report.

Command:
.\scripts\paper_trading\hqe_recorded_data_replay_readiness.bat

Optional recorded root:
.\scripts\paper_trading\hqe_recorded_data_replay_readiness.bat --recorded-root data\recorded

Optional minimum event rule:
.\scripts\paper_trading\hqe_recorded_data_replay_readiness.bat --min-events 100

Optional warning policy:
.\scripts\paper_trading\hqe_recorded_data_replay_readiness.bat --allow-warnings

Optional dry-run limit:
.\scripts\paper_trading\hqe_recorded_data_replay_readiness.bat --max-records 100

Default outputs:
- reports\paper_trading\recorded_data_replay_dataset
- reports\paper_trading\recorded_data_replay_quality_gate
- reports\paper_trading\recorded_data_replay_dry_run
- reports\paper_trading\recorded_data_replay_evidence
- reports\paper_trading\recorded_data_replay_acceptance
- reports\paper_trading\recorded_data_replay_readiness

Safety boundary:
This module is paper/evidence only. It does not run strategies, create trade plans, connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
