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
  "hqe_market_day_watch_state_snapshot.py",
  "hqe_5m_candle_cache_rotator.py",
  "hqe_data_only_poll_result_normalizer.py",
  "hqe_intraday_paper_decision_state_machine.py",
  "hqe_no_trade_reason_taxonomy_pack.py",
  "hqe_paper_trade_journal_template.py",
  "hqe_daily_evidence_backup_pack.py",
  "hqe_session_restart_recovery_snapshot.py",
  "hqe_dashboard_v5_validation_ops.py",
  "hqe_end_of_day_evaluator_bridge.py",
  "hqe_trade_day_quality_scorecard.py",
  "hqe_weekly_validation_summary_pack.py",
  "hqe_validation_drift_monitor.py",
  "hqe_fyers_error_code_triage_pack.py",
  "hqe_operator_daily_checklist_v2.py",
  "hqe_paper_watch_replay_pack.py",
  "hqe_evidence_integrity_hash_pack.py",
  "hqe_safe_startup_preflight_gate.py",
  "hqe_30_day_validation_review_board_pack.py",
  "hqe_validation_ops_master_freeze_pack.py"
)

foreach ($Script in $Scripts) {
  Write-Host "RUNNING $Script"
  & $Py (Join-Path "scripts" $Script) --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --user-id $UserId --symbol $Symbol --write
  if ($LASTEXITCODE -ne 0) { throw "$Script failed" }
}

Write-Host "MODULES_211_230_VALIDATION_OPS_STABILITY_SAFE_RUN_COMPLETE"
