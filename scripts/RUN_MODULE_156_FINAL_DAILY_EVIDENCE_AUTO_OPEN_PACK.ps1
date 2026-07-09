param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$TradingDate = "2026-07-09",
  [int]$DayNumber = 1
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

& $Python "scripts\hqe_final_daily_evidence_auto_open_pack.py" --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --write
