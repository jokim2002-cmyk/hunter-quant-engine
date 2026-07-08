@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Live Safety Lock Check ===
echo Checks disabled-by-default live safety lock.
echo This is not live trading. Real money and broker execution remain disabled.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Run this from the HQE repo after setting up the virtual environment.
    exit /b 1
)

".venv\Scripts\python.exe" -m src.paper_trading.live_safety_lock
if errorlevel 1 exit /b 1

echo.
echo === Done ===
echo Live trading remains disabled.
echo Real money remains disabled.
echo Broker execution remains disabled.
endlocal
