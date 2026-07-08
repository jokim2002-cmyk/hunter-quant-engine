@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Paper Evidence Aggregate ===
echo Aggregates local paper evidence into one safety-gated summary.
echo No broker. No live market data. No real orders.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Run this from the HQE repo after setting up the virtual environment.
    exit /b 1
)

".venv\Scripts\python.exe" -m src.paper_trading.paper_evidence_aggregate
if errorlevel 1 exit /b 1

echo.
echo === Done ===
echo Paper evidence is simulation only.
endlocal
