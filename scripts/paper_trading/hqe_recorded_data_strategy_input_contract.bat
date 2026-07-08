@echo off
setlocal

if not exist ".\.venv\Scripts\python.exe" (
    echo Missing .\.venv\Scripts\python.exe
    exit /b 1
)

.\.venv\Scripts\python.exe -m src.paper_trading.recorded_data_strategy_input_contract %*
exit /b %ERRORLEVEL%
