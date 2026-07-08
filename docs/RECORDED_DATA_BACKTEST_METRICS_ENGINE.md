# Recorded Data Backtest Metrics Engine

Module AAA converts paper-only backtest ledger rows into paper-only backtest metrics.

Purpose:
The metrics engine reads the backtest trade ledger and writes simulated reference metrics for the future backtest report writer.

Command:
.\scripts\paper_trading\hqe_recorded_data_backtest_metrics_engine.bat

Default input:
reports\paper_trading\recorded_data_backtest_trade_ledger\backtest_trade_ledger.json

Default output:
reports\paper_trading\recorded_data_backtest_metrics_engine

Generated files:
- backtest_metrics.json
- backtest_equity_curve.jsonl
- backtest_equity_curve.csv
- backtest_metrics.txt
- manifest.json

Paper metrics:
- trade count
- win/loss/flat count
- win rate percent
- loss rate percent
- simulated gross result total
- average trade result
- final equity reference
- max drawdown reference
- max drawdown percent reference

Safety boundary:
This is a paper-only backtest metrics engine. It does not connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- Completed total before Module AAA: 52 modules.
- v1.0 pending before Module AAA: 11 modules.
- v1.0 pending after Module AAA: 10 modules.
