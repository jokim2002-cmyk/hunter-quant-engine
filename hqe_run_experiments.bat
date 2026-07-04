@echo off
cd /d "%~dp0"

echo.
echo ================================
echo HQE STRATEGY EXPERIMENT RUNNER
echo ================================
echo.
echo WARNING:
echo This executes strategy experiments on market data.
echo Recommended machine: PC only.
echo Do NOT run this on laptop if it overheats or shuts down.
echo.
echo Press CTRL+C to cancel.
echo Press any key to continue on PC.
pause >nul

if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe scripts\run_strategy_experiments.py --execute --input "data\raw\fyers_nifty_5min.csv"
) else (
    py scripts\run_strategy_experiments.py --execute --input "data\raw\fyers_nifty_5min.csv"
)

echo.
echo ================================
echo EXPERIMENT OUTPUTS
echo ================================
echo.
echo Report:
echo data\processed\strategy_experiment_report.txt
echo.
echo Summary:
echo data\processed\strategy_experiment_summary.csv
echo.
echo Experiment files:
echo data\processed\experiments\
echo.

pause
