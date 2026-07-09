param(
    [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"
)

$ErrorActionPreference = "Stop"
$PythonExe = Join-Path (Get-Location) ".venv\Scripts\python.exe"

& $PythonExe "scripts\evaluate_forward_validation_day_ledger.py" --workspace $Workspace --write

