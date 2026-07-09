param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$TradingDate = "2026-07-09",
  [int]$DayNumber = 1,
  [string]$UserId = "jokim-local",
  [string]$Symbol = "NSE:NIFTY50-INDEX"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"

$Scripts = @(
  "hqe_fyers_token_refresh_helper_dashboard_integration.py",
  "hqe_visual_dashboard_v2_launcher_fix.py",
  "hqe_fyers_data_only_health_monitor.py",
  "hqe_live_5m_normalized_data_bridge.py",
  "hqe_live_paper_signal_feed_bridge.py",
  "hqe_live_paper_session_controller.py",
  "hqe_visual_dashboard_v3_operator_app.py",
  "hqe_paper_live_daily_close_plan.py",
  "hqe_fyers_token_refresh_sop_pack.py",
  "hqe_live_paper_operation_final_close_pack.py"
)

foreach ($Script in $Scripts) {
  Write-Host "RUNNING $Script"
  & $Py (Join-Path "scripts" $Script) --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --user-id $UserId --symbol $Symbol --write
  if ($LASTEXITCODE -ne 0) { throw "$Script failed" }
}

Write-Host "MODULES_181_190_SAFE_RUN_COMPLETE"
