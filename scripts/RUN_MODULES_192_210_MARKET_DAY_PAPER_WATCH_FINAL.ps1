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
  "hqe_auto_paper_watch_loop_evidence_logger.py",
  "hqe_intraday_5m_poll_scheduler_plan.py",
  "hqe_paper_signal_reason_timeline_logger.py",
  "hqe_no_trade_reason_evidence_aggregator.py",
  "hqe_paper_trade_candidate_gate.py",
  "hqe_visual_dashboard_v4_market_watch_controls.py",
  "hqe_daily_close_auto_report_pack.py",
  "hqe_30_valid_trade_day_progress_sync.py",
  "hqe_next_market_day_startup_pack.py",
  "hqe_master_evidence_index_html_pack.py",
  "hqe_kill_switch_safety_audit.py",
  "hqe_token_expiry_reminder_preflight.py",
  "hqe_market_session_calendar_guard.py",
  "hqe_live_data_gap_detector.py",
  "hqe_paper_watch_dry_run_smoke.py",
  "hqe_desktop_one_click_launcher_pack.py",
  "hqe_operator_error_recovery_pack.py",
  "hqe_forward_validation_final_gate.py",
  "hqe_market_day_paper_watch_master_handoff_pack.py"
)

foreach ($Script in $Scripts) {
  Write-Host "RUNNING $Script"
  & $Py (Join-Path "scripts" $Script) --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --user-id $UserId --symbol $Symbol --write
  if ($LASTEXITCODE -ne 0) { throw "$Script failed" }
}

Write-Host "MODULES_192_210_MARKET_DAY_PAPER_WATCH_SAFE_RUN_COMPLETE"
