# v0.6 Recorded-Data Backtest Readiness Release

Release tag:
v0.6-recorded-data-backtest-readiness

Release purpose:
This release closes the recorded-data paper backtest readiness chain for the v1.0 Testing Edition path.

Completed chain:
- recorded data strategy replay sandbox
- LONG / SHORT / NEUTRAL decision audit
- strategy decision acceptance gate
- CE/PE paper option trade-plan simulator
- paper fill/exit simulator
- paper backtest trade ledger
- paper backtest metrics engine
- paper backtest report writer
- one-command paper backtest runner
- paper-only backtest acceptance gate
- paper-only backtest readiness gate

Main shortcuts:
- .\scripts\paper_trading\hqe_recorded_data_strategy_replay_sandbox.bat
- .\scripts\paper_trading\hqe_recorded_data_strategy_decision_audit.bat
- .\scripts\paper_trading\hqe_recorded_data_strategy_decision_acceptance.bat
- .\scripts\paper_trading\hqe_recorded_data_paper_option_trade_plan_simulator.bat
- .\scripts\paper_trading\hqe_recorded_data_paper_fill_exit_simulator.bat
- .\scripts\paper_trading\hqe_recorded_data_backtest_trade_ledger.bat
- .\scripts\paper_trading\hqe_recorded_data_backtest_metrics_engine.bat
- .\scripts\paper_trading\hqe_recorded_data_backtest_report_writer.bat
- .\scripts\paper_trading\hqe_recorded_data_one_command_backtest_runner.bat
- .\scripts\paper_trading\hqe_recorded_data_backtest_acceptance_gate.bat
- .\scripts\paper_trading\hqe_recorded_data_backtest_readiness_gate.bat

Backtest readiness scope:
The release validates that recorded replay input can flow through a paper-only NIFTY option-buy backtest chain and produce report, metrics, ledger, acceptance, and readiness evidence.

Trading safety contract:
- LONG = CE BUY paper plan only.
- SHORT = PE BUY paper plan only.
- NEUTRAL = no trade.
- No option selling.
- No broker orders.
- No live market data dependency.
- No real money.
- No profitability claim.

Out of scope:
- broker execution
- FYERS/live orders
- live market data
- real-money trading
- option selling
- profitability proof

Generated evidence:
Generated reports and data remain under ignored report paths and must not be committed.

Validation:
Expected full quick-check suite after Module FFF: 2020 passed.

Progress:
- Completed total before Module FFF: 57 modules.
- v1.0 pending before Module FFF: 6 modules.
- Completed total after Module FFF: 58 modules.
- v1.0 pending after Module FFF: 5 modules.
