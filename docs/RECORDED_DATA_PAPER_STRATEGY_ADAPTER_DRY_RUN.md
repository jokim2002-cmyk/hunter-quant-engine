# Recorded Data Paper Strategy Adapter Dry-Run

Module GG adds a paper/simulation-only adapter dry-run scaffold.

Purpose:
The dry-run reads adapter readiness and adapter request manifests, then writes deterministic dry-run events. It does not execute strategy logic.

Command:
.\scripts\paper_trading\hqe_recorded_data_paper_strategy_adapter_dry_run.bat

Default inputs:
reports\paper_trading\recorded_data_paper_strategy_adapter_readiness\paper_strategy_adapter_readiness.json
reports\paper_trading\recorded_data_paper_strategy_adapter_contract\paper_strategy_adapter_requests.jsonl

Default output:
reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run

Generated files:
- paper_strategy_adapter_dry_run.json
- paper_strategy_adapter_dry_run_events.jsonl
- paper_strategy_adapter_dry_run.txt
- manifest.json

Safety boundary:
This module is paper/evidence only. It does not execute strategy logic, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
