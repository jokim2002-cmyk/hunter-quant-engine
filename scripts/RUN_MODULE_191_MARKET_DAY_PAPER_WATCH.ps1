param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$TradingDate = "",
  [string]$UserId = "jokim-local",
  [string]$Symbol = "NSE:NIFTY50-INDEX",
  [switch]$Launch
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if ([string]::IsNullOrWhiteSpace($TradingDate)) {
  $TradingDate = Get-Date -Format "yyyy-MM-dd"
}

$ArgsList = @(
  "scripts\hqe_real_market_day_paper_watch_launcher.py",
  "--workspace", $Workspace,
  "--trading-date", $TradingDate,
  "--user-id", $UserId,
  "--symbol", $Symbol,
  "--write"
)

if ($Launch) {
  $ArgsList += "--launch"
}

& $Py @ArgsList
if ($LASTEXITCODE -ne 0) { throw "Module 191 failed" }

Write-Host "MODULE_191_MARKET_DAY_PAPER_WATCH_SAFE_RUN_COMPLETE"
