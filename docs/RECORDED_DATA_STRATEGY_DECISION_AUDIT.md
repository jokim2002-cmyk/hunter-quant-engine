# Recorded Data Strategy Decision Audit

Module VV is the first LONG / SHORT / NEUTRAL decision layer in the v1.0 Testing Edition backtest path.

Purpose:
The decision audit reads strategy replay sandbox events and creates deterministic strategy decision audit events.

Command:
.\scripts\paper_trading\hqe_recorded_data_strategy_decision_audit.bat

Default input:
reports\paper_trading\recorded_data_strategy_replay_sandbox\strategy_replay_sandbox.json

Default output:
reports\paper_trading\recorded_data_strategy_decision_audit

Generated files:
- strategy_decision_audit.json
- strategy_decision_audit_events.jsonl
- strategy_decision_audit_events.csv
- strategy_decision_audit.txt
- manifest.json

Decision mapping:
- LONG = future CE buy paper plan only.
- SHORT = future PE buy paper plan only.
- NEUTRAL = no trade.

Safety boundary:
This module is paper/simulation strategy decision audit only. It does not create CE/PE trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- Completed total before Module VV: 47 modules.
- v1.0 pending before Module VV: 16 modules.
- v1.0 pending after Module VV: 15 modules.
