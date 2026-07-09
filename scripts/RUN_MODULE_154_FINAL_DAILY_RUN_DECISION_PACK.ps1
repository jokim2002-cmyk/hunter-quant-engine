param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$TradingDate = "",
  [int]$DayNumber = 0
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
  throw "Python venv not found: $PythonExe"
}

$argsList = @(
  "scripts\hqe_final_daily_run_decision_pack.py",
  "--workspace", $Workspace,
  "--repo-root", $RepoRoot,
  "--write"
)

if ($TradingDate -ne "") {
  $argsList += @("--trading-date", $TradingDate)
}
if ($DayNumber -gt 0) {
  $argsList += @("--day-number", $DayNumber)
}

& $PythonExe @argsList
