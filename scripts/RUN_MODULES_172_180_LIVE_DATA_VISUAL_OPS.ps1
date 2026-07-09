param(
    [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
    [string]$TradingDate = "2026-07-09",
    [int]$DayNumber = 1,
    [string]$UserId = "jokim-local",
    [string]$Symbol = "NSE:NIFTY50-INDEX"
)
$ErrorActionPreference = "Stop"
$Py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
$Scripts = @(
    "hqe_fyers_live_data_only_ltp_test.py",
    "hqe_fyers_historical_5m_data_only_fetcher.py",
    "hqe_live_data_symbol_config_guard.py",
    "hqe_day2_next_paper_session_generator.py",
    "hqe_local_visual_dashboard_live_paper_v2.py",
    "hqe_one_click_live_paper_session_launcher_plan.py",
    "hqe_live_paper_report_index_v2.py",
    "hqe_startup_shortcut_installer_review_pack.py",
    "hqe_live_paper_operations_final_readiness_pack.py"
)
foreach ($Script in $Scripts) {
    Write-Host "RUNNING $Script"
    & $Py "scripts\$Script" --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --user-id $UserId --symbol $Symbol --write
    if ($LASTEXITCODE -ne 0) { throw "FAILED $Script" }
}
Write-Host "MODULES_172_180_SAFE_RUN_COMPLETE"
