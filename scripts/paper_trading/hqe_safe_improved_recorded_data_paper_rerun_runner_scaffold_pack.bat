@echo off
setlocal

if not exist ".\.venv\Scripts\python.exe" (
    echo Missing .\.venv\Scripts\python.exe
    exit /b 1
)

.\.venv\Scripts\python.exe -m src.paper_trading.safe_improved_recorded_data_paper_rerun_runner_scaffold_pack %*
exit /b %ERRORLEVEL%
