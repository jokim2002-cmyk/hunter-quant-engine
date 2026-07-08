# Recorded Data Strategy Replay Preflight

Module V adds a one-command paper/simulation-only preflight for future recorded-data paper strategy replay.

Purpose:
The preflight runs:
1. Recorded data replay readiness gate.
2. Recorded data strategy input contract.
3. Final strategy replay preflight report.

Command:
.\hqe_recorded_data_strategy_replay_preflight.bat

Optional recorded root:
.\hqe_recorded_data_strategy_replay_preflight.bat --recorded-root data\recorded

Optional event and bar rules:
.\hqe_recorded_data_strategy_replay_preflight.bat --min-events 100 --min-bars 100

Optional warning policy:
.\hqe_recorded_data_strategy_replay_preflight.bat --allow-warnings

Optional dry-run limits:
.\hqe_recorded_data_strategy_replay_preflight.bat --max-records 100 --max-events 100

Default outputs:
- reports\paper_trading\recorded_data_replay_dataset
- reports\paper_trading\recorded_data_replay_quality_gate
- reports\paper_trading\recorded_data_replay_dry_run
- reports\paper_trading\recorded_data_replay_evidence
- reports\paper_trading\recorded_data_replay_acceptance
- reports\paper_trading\recorded_data_replay_readiness
- reports\paper_trading\recorded_data_strategy_input_contract
- reports\paper_trading\recorded_data_strategy_replay_preflight

Safety boundary:
This module is paper/evidence only. It does not run strategies, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
