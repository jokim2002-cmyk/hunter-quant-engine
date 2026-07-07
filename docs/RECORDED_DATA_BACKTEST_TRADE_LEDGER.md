# Recorded Data Backtest Trade Ledger

Module ZZ converts paper fill/exit lifecycle records into a paper-only backtest trade ledger.

Purpose:
The ledger reads paper fill/exit lifecycle records and writes structured trade rows for future metrics.

Command:
.\hqe_recorded_data_backtest_trade_ledger.bat

Default input:
reports\paper_trading\recorded_data_paper_fill_exit_simulator\paper_fill_exit_simulator.json

Default output:
reports\paper_trading\recorded_data_backtest_trade_ledger

Generated files:
- backtest_trade_ledger.json
- backtest_trade_ledger_rows.jsonl
- backtest_trade_ledger_rows.csv
- backtest_trade_ledger.txt
- manifest.json

Paper result formula:
simulated_gross_result = option_points_result * quantity_lots * lot_size

Safety boundary:
This is a paper-only backtest ledger. It does not connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- Completed total before Module ZZ: 51 modules.
- v1.0 pending before Module ZZ: 12 modules.
- v1.0 pending after Module ZZ: 11 modules.
