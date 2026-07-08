# Recorded Data Paper Strategy Replay Plan Acceptance Gate

Module BB adds a paper/simulation-only acceptance gate for the no-execution replay plan from Module AA.

Purpose:
The gate reads the paper strategy replay plan and decides whether it is structurally acceptable for a future paper/simulation strategy replay phase.

Default input:
reports\paper_trading\recorded_data_paper_strategy_replay_plan\paper_strategy_replay_plan.json

Default output folder:
reports\paper_trading\recorded_data_paper_strategy_replay_plan_acceptance

Generated files:
- paper_strategy_replay_plan_acceptance.json
- paper_strategy_replay_plan_acceptance.txt
- manifest.json

Command:
.\hqe_recorded_data_paper_strategy_replay_plan_acceptance.bat

Optional rules:
.\hqe_recorded_data_paper_strategy_replay_plan_acceptance.bat --min-scenario-plans 1 --min-total-planned-bars 100

Optional warning policy:
.\hqe_recorded_data_paper_strategy_replay_plan_acceptance.bat --allow-warnings

Safety boundary:
This module is paper/evidence only. It does not run strategies, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
