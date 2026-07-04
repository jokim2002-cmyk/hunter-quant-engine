@echo off
cd /d "%~dp0"

echo.
echo ================================
echo HQE FYERS NIFTY RUNNER
echo ================================

if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe scripts\run_fyers_nifty_research.py --input "data\raw\fyers_nifty_5min.csv"
) else (
    py scripts\run_fyers_nifty_research.py --input "data\raw\fyers_nifty_5min.csv"
)

pause
