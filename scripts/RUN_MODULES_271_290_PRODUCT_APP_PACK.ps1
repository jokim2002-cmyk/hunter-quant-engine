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
  "hqe_product_app_shell.py",
  "hqe_license_activation_gate.py",
  "hqe_owner_license_generator_pack.py",
  "hqe_customer_machine_id_tool_pack.py",
  "hqe_single_desktop_icon_installer_pack.py",
  "hqe_stylish_hqe_icon_pack.py",
  "hqe_guided_login_screen_pack.py",
  "hqe_guided_fyers_connect_screen_pack.py",
  "hqe_guided_market_watch_screen_pack.py",
  "hqe_daily_report_viewer_pack.py",
  "hqe_new_pc_installer_pack.py",
  "hqe_requirements_venv_setup_pack.py",
  "hqe_app_config_folder_setup_pack.py",
  "hqe_customer_user_guide_pack.py",
  "hqe_owner_seller_guide_pack.py",
  "hqe_license_validation_tests_pack.py",
  "hqe_installer_smoke_tests_pack.py",
  "hqe_app_shortcut_repair_tool_pack.py",
  "hqe_product_handoff_pack.py",
  "hqe_product_mvp_freeze.py"
)

foreach ($Script in $Scripts) {
  Write-Host "RUNNING $Script"
  & $Py (Join-Path "scripts" $Script) --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --user-id $UserId --symbol $Symbol --write
  if ($LASTEXITCODE -ne 0) { throw "$Script failed" }
}

Write-Host "MODULES_271_290_PRODUCT_APP_PACK_SAFE_RUN_COMPLETE"
