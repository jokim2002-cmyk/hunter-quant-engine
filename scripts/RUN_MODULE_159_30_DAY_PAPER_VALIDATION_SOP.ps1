param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$TradingDate = "2026-07-09",
  [int]$DayNumber = 1
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ScriptPath = Join-Path $RepoRoot "scripts\hqe_30_day_paper_validation_daily_operating_sop.py"

& $PythonExe $ScriptPath --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --write
