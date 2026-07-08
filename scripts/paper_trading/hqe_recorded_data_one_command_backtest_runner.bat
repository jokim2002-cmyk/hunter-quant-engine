@echo off
.\.venv\Scripts\python.exe -m src.paper_trading.recorded_data_strategy_input_contract
.\.venv\Scripts\python.exe -m src.paper_trading.recorded_data_backtest_dependency_bridge
.\.venv\Scripts\python.exe -m src.paper_trading.recorded_data_one_command_backtest_runner %*
