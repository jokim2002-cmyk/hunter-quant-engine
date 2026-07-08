# Recorded Data Paper Strategy Adapter Dry-Run Acceptance Gate

Module HH adds a paper/simulation-only acceptance gate for adapter dry-run output.

Purpose:
The gate reads adapter dry-run output and decides whether dry-run events are structurally acceptable for future paper/simulation adapter evidence modules.

Command:
.\scripts\paper_trading\hqe_recorded_data_paper_strategy_adapter_dry_run_acceptance.bat

Default input:
reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run\paper_strategy_adapter_dry_run.json

Default output:
reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_acceptance

Generated files:
- paper_strategy_adapter_dry_run_acceptance.json
- paper_strategy_adapter_dry_run_acceptance.txt
- manifest.json

Safety boundary:
This module is paper/evidence only. It does not execute strategy logic, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
