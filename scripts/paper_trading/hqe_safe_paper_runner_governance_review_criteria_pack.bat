@echo off
setlocal

if not exist ".\.venv\Scripts\python.exe" (
    echo Missing .\.venv\Scripts\python.exe
    exit /b 1
)

.\.venv\Scripts\python.exe -m src.paper_trading.safe_paper_runner_governance_review_criteria_pack %*
exit /b %ERRORLEVEL%
