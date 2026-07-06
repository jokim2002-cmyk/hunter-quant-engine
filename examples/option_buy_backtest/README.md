# Option Buy Backtest Sample Data

This directory contains small synthetic/demo CSV files for the offline option-buy backtest CLI.

The sample data is synthetic/demo only. It is not real market data. It is not a profitability claim. The rows are intentionally simple so the CSV loaders, planner, and backtest runner can be smoke-tested end to end.

Run from the repository root:

```powershell
python scripts/run_option_buy_backtest.py --scenario-csv examples/option_buy_backtest/sample_scenario.csv --premium-csv examples/option_buy_backtest/sample_premium.csv
```

Write a summary JSON report:

```powershell
.
.venv\Scripts\python.exe scripts/run_option_buy_backtest.py `
  --scenario-csv examples/option_buy_backtest/sample_scenario.csv `
  --premium-csv examples/option_buy_backtest/sample_premium.csv `
  --summary-json reports/option_buy_backtest/summary.json
```

Write a summary CSV report:

```powershell
.\.venv\Scripts\python.exe scripts/run_option_buy_backtest.py `
  --scenario-csv examples/option_buy_backtest/sample_scenario.csv `
  --premium-csv examples/option_buy_backtest/sample_premium.csv `
  --summary-csv reports/option_buy_backtest/summary.csv
```

Write trade-detail JSON:

```powershell
.\.venv\Scripts\python.exe scripts/run_option_buy_backtest.py `
  --scenario-csv examples/option_buy_backtest/sample_scenario.csv `
  --premium-csv examples/option_buy_backtest/sample_premium.csv `
  --trades-json reports/option_buy_backtest/trades.json
```

Write trade-detail CSV:

```powershell
.\.venv\Scripts\python.exe scripts/run_option_buy_backtest.py `
  --scenario-csv examples/option_buy_backtest/sample_scenario.csv `
  --premium-csv examples/option_buy_backtest/sample_premium.csv `
  --trades-csv reports/option_buy_backtest/trades.csv
```

Write all reports together:

```powershell
.\.venv\Scripts\python.exe scripts/run_option_buy_backtest.py `
  --scenario-csv examples/option_buy_backtest/sample_scenario.csv `
  --premium-csv examples/option_buy_backtest/sample_premium.csv `
  --summary-json reports/option_buy_backtest/summary.json `
  --summary-csv reports/option_buy_backtest/summary.csv `
  --trades-json reports/option_buy_backtest/trades.json `
  --trades-csv reports/option_buy_backtest/trades.csv
```

Generated report files should not be committed unless you intentionally want to create fixtures. They are safe local outputs only.