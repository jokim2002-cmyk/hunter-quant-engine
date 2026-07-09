
param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$TradingDate = "2026-07-09",
  [int]$DayNumber = 1
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path ".").Path
$Py = Join-Path $Root ".venv\Scripts\python.exe"

$Scripts = @(
  "hqe_fyers_data_only_secret_preflight_pack.py",
  "hqe_fyers_access_token_validation_pack.py",
  "hqe_fyers_data_only_quote_ltp_fetcher.py",
  "hqe_fyers_5m_candle_builder_live_normalizer.py",
  "hqe_live_paper_market_watch_loop.py",
  "hqe_paper_signal_execution_logger.py",
  "hqe_live_no_trade_reason_integration.py",
  "hqe_daily_auto_close_report_tracker_integration.py",
  "hqe_safe_startup_desktop_shortcut_final.py",
  "hqe_full_live_paper_dry_run_final_readiness.py"
)

foreach ($Script in $Scripts) {
  Write-Host "RUNNING $Script" -ForegroundColor Cyan
  & $Py (Join-Path "scripts" $Script) --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --write
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "MODULES_161_170_SAFE_RUN_COMPLETE" -ForegroundColor Green
