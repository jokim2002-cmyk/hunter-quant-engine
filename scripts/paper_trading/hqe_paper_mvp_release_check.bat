@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Paper MVP Release Check ===
echo Checks local paper-only release readiness.
echo No tag is created. No broker. No live market data. No real orders.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Run this from the HQE repo after setting up the virtual environment.
    exit /b 1
)

".venv\Scripts\python.exe" -m src.paper_trading.paper_mvp_release_gate
if errorlevel 1 exit /b 1

echo.
echo === Release gate passed ===
echo Tag creation is still manual after final review.
endlocal
