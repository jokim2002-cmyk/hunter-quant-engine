@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Paper Replay Journal Summary ===
echo Prints local/generated fake paper replay journal summary.
echo No broker. No live market data. No real orders.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Run this from the HQE repo after setting up the virtual environment.
    exit /b 1
)

".venv\Scripts\python.exe" -m src.paper_trading.paper_trading_replay_journal_summary_cli
if errorlevel 1 exit /b 1

echo.
echo === Done ===
endlocal
