@echo off
setlocal

if not exist ".\.venv\Scripts\python.exe" (
    echo Missing .\.venv\Scripts\python.exe
    exit /b 1
)

.\.venv\Scripts\python.exe -m src.paper_trading.paper_exit_rule_sensitivity_review_pack %*
exit /b %ERRORLEVEL%
