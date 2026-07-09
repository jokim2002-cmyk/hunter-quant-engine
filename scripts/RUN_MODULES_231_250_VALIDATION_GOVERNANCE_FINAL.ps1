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
  "hqe_validation_day_auto_rollover_plan.py",
  "hqe_missing_evidence_detector.py",
  "hqe_paper_pnl_aggregator_safe.py",
  "hqe_trade_day_eligibility_auditor.py",
  "hqe_expiry_week_progress_tracker.py",
  "hqe_dashboard_v6_validation_governance.py",
  "hqe_daily_html_report_builder.py",
  "hqe_secure_env_reload_helper.py",
  "hqe_data_replay_verifier.py",
  "hqe_watch_loop_crash_resume_marker.py",
  "hqe_paper_execution_gate_no_fake.py",
  "hqe_no_trade_day_non_count_lock.py",
  "hqe_validation_master_ledger_reconciler.py",
  "hqe_operator_command_center_shortcuts.py",
  "hqe_remote_safe_handoff_bundle.py",
  "hqe_evidence_archive_indexer.py",
  "hqe_final_30_day_readiness_gate.py",
  "hqe_pre_real_money_review_checklist.py",
  "hqe_validation_governance_freeze_pack.py",
  "hqe_master_system_status_dashboard.py"
)

foreach ($Script in $Scripts) {
  Write-Host "RUNNING $Script"
  & $Py (Join-Path "scripts" $Script) --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --user-id $UserId --symbol $Symbol --write
  if ($LASTEXITCODE -ne 0) { throw "$Script failed" }
}

Write-Host "MODULES_231_250_VALIDATION_GOVERNANCE_FINAL_SAFE_RUN_COMPLETE"
