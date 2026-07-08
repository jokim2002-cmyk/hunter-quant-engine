# Recorded Data Backtest Report Writer

Module BBB packages paper-only backtest metrics and trade ledger rows into a readable paper-only backtest report bundle.

Purpose:
The report writer reads the metrics engine output and the trade ledger output, validates both, and writes a final report bundle for the future one-command backtest runner.

Command:
.\scripts\paper_trading\hqe_recorded_data_backtest_report_writer.bat

Default inputs:
reports\paper_trading\recorded_data_backtest_metrics_engine\backtest_metrics.json
reports\paper_trading\recorded_data_backtest_trade_ledger\backtest_trade_ledger.json

Default output:
reports\paper_trading\recorded_data_backtest_report_writer

Generated files:
- backtest_report.json
- backtest_report.txt
- backtest_report_summary.csv
- backtest_report_trade_preview.jsonl
- manifest.json

Paper report summary:
- trade count
- win/loss/flat count
- win rate percent
- simulated gross result total
- average trade result
- final equity reference
- max drawdown reference
- max drawdown percent reference

Safety boundary:
This is a paper-only backtest report. It does not connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- Completed total before Module BBB: 53 modules.
- v1.0 pending before Module BBB: 10 modules.
- v1.0 pending after Module BBB: 9 modules.
