# Recorded Data One-Command Backtest Runner

Module CCC runs the recorded-data paper backtest chain with one command.

Purpose:
The runner orchestrates the v1.0 Testing Edition paper backtest path.

Command:
.\scripts\paper_trading\hqe_recorded_data_one_command_backtest_runner.bat

Default inputs:
reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness\paper_strategy_adapter_dry_run_consumer_evidence_readiness.json
reports\paper_trading\recorded_data_strategy_input_contract\strategy_input_bars.jsonl

Default output:
reports\paper_trading\recorded_data_one_command_backtest_runner

Stage chain:
- strategy replay sandbox
- LONG / SHORT / NEUTRAL decision audit
- strategy decision acceptance
- CE/PE paper option trade-plan simulator
- paper fill/exit simulator
- paper backtest trade ledger
- paper backtest metrics engine
- paper backtest report writer

Generated files:
- one_command_backtest_runner.json
- one_command_backtest_runner.txt
- manifest.json

One-command paper backtest safety:
- LONG = CE BUY paper plan only.
- SHORT = PE BUY paper plan only.
- NEUTRAL = no trade.
- No option selling.
- No broker orders.
- No live market data.
- No real money.

Safety boundary:
This is a paper-only recorded-data one-command paper backtest runner. It does not connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- Completed total before Module CCC: 54 modules.
- v1.0 pending before Module CCC: 9 modules.
- v1.0 pending after Module CCC: 8 modules.
