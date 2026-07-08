# Recorded Data Strategy Input Contract

Module U adds a paper/simulation-only strategy input contract for recorded-data replay dry-run events.

Purpose:
The contract converts replay dry-run events into structurally safe bars for a future paper/simulation strategy replay phase.

Default input:
reports\paper_trading\recorded_data_replay_dry_run\dry_run_events.jsonl

Default output folder:
reports\paper_trading\recorded_data_strategy_input_contract

Generated files:
- strategy_input_contract.json
- strategy_input_bars.jsonl
- strategy_input_contract.txt
- manifest.json

Command:
.\scripts\paper_trading\hqe_recorded_data_strategy_input_contract.bat

Optional minimum bar rule:
.\scripts\paper_trading\hqe_recorded_data_strategy_input_contract.bat --min-bars 100

Optional event limit:
.\scripts\paper_trading\hqe_recorded_data_strategy_input_contract.bat --max-events 100

Checks:
- dry-run events JSONL exists
- dry-run event lines are JSON objects
- event type is recorded_market_data_bar
- timestamp and close are available
- execution/trading/profit fields are not present
- accepted bar count meets the configured minimum

Safety boundary:
This module is paper/evidence only. It does not run strategies, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
