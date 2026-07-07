# Recorded Data Backtest Acceptance Gate

Module DDD validates the one-command recorded-data paper backtest runner output.

Purpose:
The acceptance gate checks that the paper-only backtest chain completed and is acceptable for the future v1.0 testing release gate.

Command:
.\hqe_recorded_data_backtest_acceptance_gate.bat

Default input:
reports\paper_trading\recorded_data_one_command_backtest_runner\one_command_backtest_runner.json

Default output:
reports\paper_trading\recorded_data_backtest_acceptance_gate

Generated files:
- backtest_acceptance_gate.json
- backtest_acceptance_gate.txt
- manifest.json

Acceptance checks:
- runner status is pass
- runner is ready for backtest acceptance
- expected 8 paper backtest stages are present
- stages are ready
- final backtest report path is present
- final metrics path is present
- final trade ledger path is present
- final files exist on disk by default

Paper-only backtest acceptance gate safety:
- LONG = CE BUY paper plan only.
- SHORT = PE BUY paper plan only.
- NEUTRAL = no trade.
- No option selling.
- No broker orders.
- No live market data.
- No real money.

Safety boundary:
This is a paper-only backtest acceptance gate. It does not connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- Completed total before Module DDD: 55 modules.
- v1.0 pending before Module DDD: 8 modules.
- v1.0 pending after Module DDD: 7 modules.
