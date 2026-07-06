# Option Buy Backtest Sample Data

This directory contains small synthetic/demo CSV files for the offline option-buy backtest CLI.

The data is not real market data. It is not a profitability claim. The rows are intentionally simple so the CSV loaders, planner, and backtest runner can be smoke-tested end to end.

Run from the repository root:

```powershell
python scripts/run_option_buy_backtest.py --scenario-csv examples/option_buy_backtest/sample_scenario.csv --premium-csv examples/option_buy_backtest/sample_premium.csv
```