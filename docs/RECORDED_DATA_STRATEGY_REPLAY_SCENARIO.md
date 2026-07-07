# Recorded Data Strategy Replay Scenario Manifest

Module W adds a paper/simulation-only scenario manifest for future recorded-data paper strategy replay.

Purpose:
The scenario manifest packages accepted strategy input bars into deterministic replay scenarios grouped by recorded source file.

Default inputs:
reports\paper_trading\recorded_data_strategy_input_contract\strategy_input_bars.jsonl
reports\paper_trading\recorded_data_strategy_replay_preflight\preflight_report.json

Default output folder:
reports\paper_trading\recorded_data_strategy_replay_scenario

Generated files:
- scenario_manifest.json
- scenarios.jsonl
- scenario_manifest.txt
- manifest.json

Command:
.\hqe_recorded_data_strategy_replay_scenario.bat

Optional minimum bars per scenario:
.\hqe_recorded_data_strategy_replay_scenario.bat --min-bars-per-scenario 100

Optional scenario limit:
.\hqe_recorded_data_strategy_replay_scenario.bat --max-scenarios 5

Checks:
- strategy input bars JSONL exists
- strategy input bars are JSON objects
- bars are recorded_replay and paper_simulation_only
- strategy replay preflight is ready
- source groups meet the configured minimum bar count

Safety boundary:
This module is paper/evidence only. It does not run strategies, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
