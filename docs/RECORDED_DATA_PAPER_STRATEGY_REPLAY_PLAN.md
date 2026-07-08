# Recorded Data Paper Strategy Replay Plan

Module AA adds a no-execution paper/simulation-only strategy replay plan scaffold.

Purpose:
The replay plan reads scenario readiness, scenario manifest, and strategy input bars, then creates deterministic scenario replay plans for a future paper strategy replay phase.

Default inputs:
reports\paper_trading\recorded_data_strategy_replay_scenario_readiness\scenario_readiness_report.json
reports\paper_trading\recorded_data_strategy_replay_scenario\scenario_manifest.json
reports\paper_trading\recorded_data_strategy_input_contract\strategy_input_bars.jsonl

Default output folder:
reports\paper_trading\recorded_data_paper_strategy_replay_plan

Generated files:
- paper_strategy_replay_plan.json
- paper_strategy_replay_plans.jsonl
- paper_strategy_replay_plan.txt
- manifest.json

Command:
.\hqe_recorded_data_paper_strategy_replay_plan.bat

Optional rules:
.\hqe_recorded_data_paper_strategy_replay_plan.bat --min-scenarios 1 --min-bars 100

Optional warning policy:
.\hqe_recorded_data_paper_strategy_replay_plan.bat --allow-warnings

Safety boundary:
This module is paper/evidence only. It does not run strategies, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
