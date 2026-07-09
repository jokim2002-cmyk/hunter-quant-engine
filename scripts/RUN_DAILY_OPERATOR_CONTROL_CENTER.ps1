param(
    [string]$RepoRoot = "D:\Hunter_Quant_Engine_PC_TRANSFER",
    [string]$RunsRoot = "D:\HQE_BACKTEST_RUNS",
    [switch]$ExecuteApprovedSteps
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $RepoRoot

$python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$script = Join-Path $RepoRoot "scripts\run_daily_operator_control_center.py"

if (-not (Test-Path $python)) {
    throw "Python venv not found: $python"
}

if (-not (Test-Path $script)) {
    throw "Module 144 script not found: $script"
}

$argsList = @(
    $script,
    "--repo-root", $RepoRoot,
    "--runs-root", $RunsRoot,
    "--python-exe", $python,
    "--print-summary"
)

if ($ExecuteApprovedSteps) {
    $argsList += "--execute-approved-steps"
}

& $python @argsList

Write-Host ""
Write-Host "Safety: paper-only, no real money, no broker execution, no real orders, no auto trading, no option selling, no external API, no profitability claim."
