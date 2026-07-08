# Recorded Data Paper Option Trade-Plan Simulator

Module XX converts accepted LONG / SHORT / NEUTRAL decision audit events into paper-only NIFTY option buy trade plans.

Purpose:
The simulator reads the strategy decision acceptance gate and strategy decision audit report, then creates safe paper option buy plans.

Command:
.\scripts\paper_trading\hqe_recorded_data_paper_option_trade_plan_simulator.bat

Default inputs:
reports\paper_trading\recorded_data_strategy_decision_acceptance\strategy_decision_acceptance.json
reports\paper_trading\recorded_data_strategy_decision_audit\strategy_decision_audit.json

Default output:
reports\paper_trading\recorded_data_paper_option_trade_plan_simulator

Generated files:
- paper_option_trade_plan_simulator.json
- paper_option_trade_plans.jsonl
- paper_option_trade_plan_simulator.txt
- manifest.json

Plan mapping:
- LONG = CE BUY paper plan only.
- SHORT = PE BUY paper plan only.
- NEUTRAL = no trade.

Safety boundary:
This module is paper/simulation option trade-plan simulation only. It does not simulate fills, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- Completed total before Module XX: 49 modules.
- v1.0 pending before Module XX: 14 modules.
- v1.0 pending after Module XX: 13 modules.
