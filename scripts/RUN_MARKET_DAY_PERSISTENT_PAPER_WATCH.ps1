param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$TradingDate = "",
  [int]$DayNumber = 1,
  [string]$UserId = "jokim-local",
  [string]$Symbol = "NSE:NIFTY50-INDEX",
  [int]$IntervalSeconds = 300,
  [int]$MaxCycles = 0,
  [switch]$Once,
  [switch]$RunDataFetch,
  [switch]$IgnoreMarketWindow,
  [switch]$InstallLauncher
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if ([string]::IsNullOrWhiteSpace($TradingDate)) {
  $TradingDate = Get-Date -Format "yyyy-MM-dd"
}

if ($InstallLauncher) {
  New-Item -ItemType Directory -Force $Workspace | Out-Null
  $Launcher = Join-Path $Workspace "START_HQE_MARKET_DAY_PAPER_WATCH_0915_1530.cmd"
  $Content = @"
@echo off
title HQE Persistent Market-Day Paper Watch 0915-1530
cd /d "$RepoRoot"
echo HQE PERSISTENT MARKET-DAY PAPER WATCH
echo Safety: PAPER ONLY / DATA ONLY / NO ORDERS / NO BROKER EXECUTION / NO AUTO TRADING
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\RUN_MARKET_DAY_PERSISTENT_PAPER_WATCH.ps1" -Workspace "$Workspace" -TradingDate "$TradingDate" -DayNumber $DayNumber -UserId "$UserId" -Symbol "$Symbol" -IntervalSeconds $IntervalSeconds -RunDataFetch
echo.
echo Watch loop ended. Press any key to close.
pause
"@
  Set-Content -Path $Launcher -Value $Content -Encoding UTF8
  Write-Host "INSTALLED_PERSISTENT_WATCH_LAUNCHER $Launcher"
  exit 0
}

$ArgsList = @(
  "scripts\hqe_market_day_persistent_paper_watch_loop.py",
  "--workspace", $Workspace,
  "--trading-date", $TradingDate,
  "--day-number", "$DayNumber",
  "--user-id", $UserId,
  "--symbol", $Symbol,
  "--interval-seconds", "$IntervalSeconds"
)

if ($MaxCycles -gt 0) {
  $ArgsList += @("--max-cycles", "$MaxCycles")
}

if ($Once) {
  $ArgsList += "--once"
}

if ($RunDataFetch) {
  $ArgsList += "--run-data-fetch"
}

if ($IgnoreMarketWindow) {
  $ArgsList += "--ignore-market-window"
}

& $Py @ArgsList
if ($LASTEXITCODE -ne 0) { throw "Persistent market-day paper watch failed" }

Write-Host "PERSISTENT_MARKET_DAY_PAPER_WATCH_SAFE_RUN_COMPLETE"
