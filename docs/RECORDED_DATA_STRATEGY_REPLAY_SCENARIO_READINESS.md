# Recorded Data Strategy Replay Scenario Readiness Gate

Module Y adds a one-command paper/simulation-only scenario readiness gate for future recorded-data paper strategy replay.

Purpose:
The scenario readiness gate runs:
1. Recorded data strategy replay preflight.
2. Recorded data strategy replay scenario manifest.
3. Recorded data strategy replay scenario acceptance gate.
4. Final scenario readiness report.

Command:
.\scripts\paper_trading\hqe_recorded_data_strategy_replay_scenario_readiness.bat

Optional recorded root:
.\scripts\paper_trading\hqe_recorded_data_strategy_replay_scenario_readiness.bat --recorded-root data\recorded

Optional readiness rules:
.\scripts\paper_trading\hqe_recorded_data_strategy_replay_scenario_readiness.bat --min-events 100 --min-bars 100 --min-scenarios 1 --min-bars-per-scenario 100

Optional warning policy:
.\scripts\paper_trading\hqe_recorded_data_strategy_replay_scenario_readiness.bat --allow-warnings

Optional limits:
.\scripts\paper_trading\hqe_recorded_data_strategy_replay_scenario_readiness.bat --max-records 100 --max-events 100 --max-scenarios 5

Default outputs:
- reports\paper_trading\recorded_data_replay_dataset
- reports\paper_trading\recorded_data_replay_quality_gate
- reports\paper_trading\recorded_data_replay_dry_run
- reports\paper_trading\recorded_data_replay_evidence
- reports\paper_trading\recorded_data_replay_acceptance
- reports\paper_trading\recorded_data_replay_readiness
- reports\paper_trading\recorded_data_strategy_input_contract
- reports\paper_trading\recorded_data_strategy_replay_preflight
- reports\paper_trading\recorded_data_strategy_replay_scenario
- reports\paper_trading\recorded_data_strategy_replay_scenario_acceptance
- reports\paper_trading\recorded_data_strategy_replay_scenario_readiness

Safety boundary:
This module is paper/evidence only. It does not run strategies, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
