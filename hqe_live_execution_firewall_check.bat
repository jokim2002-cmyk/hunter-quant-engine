@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Live Execution Firewall Check ===
echo Checks deny-only firewall for future live-readiness order intents.
echo This is not live trading. No broker. No live market data. No real orders.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Run this from the HQE repo after setting up the virtual environment.
    exit /b 1
)

".venv\Scripts\python.exe" -m src.paper_trading.live_execution_firewall
if errorlevel 1 exit /b 1

echo.
echo === Done ===
echo Live order intent remains denied.
echo Real money remains disabled.
echo Broker submission remains disabled.
endlocal
