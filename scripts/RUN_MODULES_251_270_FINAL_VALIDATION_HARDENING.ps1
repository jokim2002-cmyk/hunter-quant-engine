param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$TradingDate = "",
  [int]$DayNumber = 1,
  [string]$UserId = "jokim-local",
  [string]$Symbol = "NSE:NIFTY50-INDEX"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if ([string]::IsNullOrWhiteSpace($TradingDate)) {
  $TradingDate = Get-Date -Format "yyyy-MM-dd"
}

$Scripts = @(
  "hqe_daily_run_manifest_generator.py",
  "hqe_manual_market_holiday_override_guard.py",
  "hqe_valid_trade_day_acceptance_criteria_engine.py",
  "hqe_forward_validation_kpi_snapshot.py",
  "hqe_evidence_export_zip_pack.py",
  "hqe_critical_blocker_banner_pack.py",
  "hqe_stale_token_data_age_checker.py",
  "hqe_end_to_end_operator_rehearsal_pack.py",
  "hqe_paper_signal_latency_tracker.py",
  "hqe_safe_config_snapshot.py",
  "hqe_workspace_cleanup_review_plan.py",
  "hqe_validation_anomaly_detector.py",
  "hqe_daily_summary_clipboard_pack.py",
  "hqe_no_broker_api_static_scanner.py",
  "hqe_final_daily_evidence_bundle.py",
  "hqe_monthly_validation_pack.py",
  "hqe_dashboard_v7_final_validation_hardening.py",
  "hqe_supervisory_review_memo_pack.py",
  "hqe_go_no_go_governance_freeze.py",
  "hqe_master_readiness_freeze_final.py"
)

foreach ($Script in $Scripts) {
  Write-Host "RUNNING $Script"
  & $Py (Join-Path "scripts" $Script) --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --user-id $UserId --symbol $Symbol --write
  if ($LASTEXITCODE -ne 0) { throw "$Script failed" }
}

Write-Host "MODULES_251_270_FINAL_VALIDATION_HARDENING_SAFE_RUN_COMPLETE"
