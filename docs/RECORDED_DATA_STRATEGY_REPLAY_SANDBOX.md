# Recorded Data Strategy Replay Sandbox

Module UU starts the v1.0 Testing Edition backtest path.

Purpose:
The sandbox reads validated recorded-data strategy input bars and converts them into deterministic strategy replay sandbox events.

Command:
.\hqe_recorded_data_strategy_replay_sandbox.bat

Default inputs:
reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness\paper_strategy_adapter_dry_run_consumer_evidence_readiness.json
reports\paper_trading\recorded_data_strategy_input_contract\strategy_input_bars.jsonl

Default output:
reports\paper_trading\recorded_data_strategy_replay_sandbox

Generated files:
- strategy_replay_sandbox.json
- strategy_replay_sandbox_events.jsonl
- strategy_replay_sandbox.txt
- manifest.json

Safety boundary:
This module is paper/simulation backtest sandbox only. It does not generate LONG/SHORT/NEUTRAL signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- Completed total before Module UU: 46 modules.
- v1.0 pending before Module UU: 17 modules.
- v1.0 pending after Module UU: 16 modules.
