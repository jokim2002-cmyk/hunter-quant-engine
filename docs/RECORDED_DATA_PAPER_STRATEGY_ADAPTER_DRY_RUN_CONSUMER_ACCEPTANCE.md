# Recorded Data Paper Strategy Adapter Dry-Run Consumer Acceptance Gate

Module OO adds a paper/simulation-only acceptance gate for adapter dry-run consumer output.

Purpose:
The gate reads the adapter dry-run consumer report and validates consumed events before future consumer readiness/evidence modules can consume them.

Command:
.\scripts\paper_trading\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance.bat

Default input:
reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer\paper_strategy_adapter_dry_run_consumer.json

Default output:
reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance

Generated files:
- paper_strategy_adapter_dry_run_consumer_acceptance.json
- paper_strategy_adapter_dry_run_consumer_acceptance.txt
- manifest.json

Safety boundary:
This module is paper/evidence only. It does not execute strategy logic, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
