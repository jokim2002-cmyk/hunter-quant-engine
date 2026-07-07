@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Recorded Data Evidence Inventory ===
echo Scans local recorded/historical data folders for evidence pipeline readiness.
echo No broker. No live market data. No real orders.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Run this from the HQE repo after setting up the virtual environment.
    exit /b 1
)

".venv\Scripts\python.exe" -m src.paper_trading.recorded_data_inventory
if errorlevel 1 exit /b 1

echo.
echo === Done ===
echo This inventory is not a profitability claim.
endlocal
