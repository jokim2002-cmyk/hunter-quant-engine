@echo off
setlocal EnableExtensions
cd /d %~dp0
set "HQE_WORKSPACE=D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"
set "HQE_PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%HQE_PYTHON%" (
  echo HQE venv Python not found:
  echo %HQE_PYTHON%
  pause
  exit /b 1
)

start "" "%HQE_PYTHON%" "%~dp0scripts\hqe_operator_live_status_dashboard.py" --workspace "%HQE_WORKSPACE%"
endlocal
