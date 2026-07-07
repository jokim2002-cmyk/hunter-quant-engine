@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Live Readiness Check ===
echo Checks whether paper evidence allows live-readiness engineering.
echo This does NOT enable real money or broker execution.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Run this from the HQE repo after setting up the virtual environment.
    exit /b 1
)

".venv\Scripts\python.exe" -m src.paper_trading.live_readiness_gate
if errorlevel 1 exit /b 1

echo.
echo === Done ===
echo Real money remains disabled.
echo Broker execution remains disabled.
endlocal
