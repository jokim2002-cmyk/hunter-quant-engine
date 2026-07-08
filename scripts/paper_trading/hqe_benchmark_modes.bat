@echo off
cd /d "%~dp0"

echo.
echo ================================
echo HQE STRATEGY MODE BENCHMARK
echo ================================
echo.
echo WARNING:
echo This is a heavy full-data benchmark.
echo Recommended machine: PC only.
echo Do NOT run this on laptop if it overheats or shuts down.
echo.
echo Press CTRL+C to cancel.
echo Press any key to continue on PC.
pause >nul

if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe scripts\benchmark_strategy_modes.py --input "data\raw\fyers_nifty_5min.csv"
) else (
    py scripts\benchmark_strategy_modes.py --input "data\raw\fyers_nifty_5min.csv"
)

echo.
echo ================================
echo BENCHMARK OUTPUTS
echo ================================
echo.
echo Report:
echo data\processed\fyers_nifty_5m_mode_benchmark_report.txt
echo.
echo Summary:
echo data\processed\fyers_nifty_5m_mode_benchmark_summary.csv
echo.

pause
