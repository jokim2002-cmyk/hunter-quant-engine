# Recorded Data Strategy Replay Scenario Acceptance Gate

Module X adds a paper/simulation-only acceptance gate for future recorded-data paper strategy replay scenarios.

Purpose:
The gate reads the scenario manifest from Module W and decides whether the scenarios are structurally acceptable for a future paper/simulation strategy replay phase.

Default input:
reports\paper_trading\recorded_data_strategy_replay_scenario\scenario_manifest.json

Default output folder:
reports\paper_trading\recorded_data_strategy_replay_scenario_acceptance

Generated files:
- scenario_acceptance.json
- scenario_acceptance.txt
- manifest.json

Command:
.\scripts\paper_trading\hqe_recorded_data_strategy_replay_scenario_acceptance.bat

Optional minimum scenario and bar rules:
.\scripts\paper_trading\hqe_recorded_data_strategy_replay_scenario_acceptance.bat --min-scenarios 1 --min-bars-per-scenario 100

Optional warning policy:
.\scripts\paper_trading\hqe_recorded_data_strategy_replay_scenario_acceptance.bat --allow-warnings

Checks:
- scenario manifest exists and is valid JSON
- manifest status is pass unless warnings are explicitly allowed
- minimum scenario count is met
- each scenario meets minimum bar count
- each scenario is recorded_replay and paper_simulation_only
- scenario identity/source/timestamp fields are present

Safety boundary:
This module is paper/evidence only. It does not run strategies, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
