# Recorded Data Paper Fill and Exit Simulator

Module YY converts CE/PE paper option trade plans into deterministic paper entry/exit lifecycle events.

Purpose:
The simulator reads paper option trade plans and strategy decision audit close references, then creates paper-only fill/exit lifecycle records for the future backtest ledger.

Command:
.\hqe_recorded_data_paper_fill_exit_simulator.bat

Default inputs:
reports\paper_trading\recorded_data_paper_option_trade_plan_simulator\paper_option_trade_plan_simulator.json
reports\paper_trading\recorded_data_strategy_decision_audit\strategy_decision_audit.json

Default output:
reports\paper_trading\recorded_data_paper_fill_exit_simulator

Generated files:
- paper_fill_exit_simulator.json
- paper_fill_exit_lifecycles.jsonl
- paper_fill_exit_simulator.txt
- manifest.json

Paper lifecycle mapping:
- LONG / CE BUY paper plan benefits when underlying close moves up.
- SHORT / PE BUY paper plan benefits when underlying close moves down.
- NEUTRAL creates no trade and is not filled.
- Broker execution remains disabled.

Safety boundary:
This module is paper/simulation fill and exit simulation only. It does not connect to a broker, request live market data, place real orders, use real money, calculate account PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- Completed total before Module YY: 50 modules.
- v1.0 pending before Module YY: 13 modules.
- v1.0 pending after Module YY: 12 modules.
