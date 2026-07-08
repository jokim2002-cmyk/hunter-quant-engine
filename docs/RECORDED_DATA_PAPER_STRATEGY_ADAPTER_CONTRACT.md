# Recorded Data Paper Strategy Adapter Contract

Module DD adds a no-execution adapter contract for future paper strategy replay.

Purpose:
The contract reads the plan readiness report and the paper strategy replay plan, then creates adapter request manifests for a future paper/simulation strategy adapter.

Command:
.\hqe_recorded_data_paper_strategy_adapter_contract.bat

Default inputs:
reports\paper_trading\recorded_data_paper_strategy_replay_plan_readiness\paper_strategy_replay_plan_readiness.json
reports\paper_trading\recorded_data_paper_strategy_replay_plan\paper_strategy_replay_plan.json

Default output:
reports\paper_trading\recorded_data_paper_strategy_adapter_contract

Generated files:
- paper_strategy_adapter_contract.json
- paper_strategy_adapter_requests.jsonl
- paper_strategy_adapter_contract.txt
- manifest.json

Safety boundary:
This module is paper/evidence only. It does not execute strategy logic, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
