param(
    [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
    [string]$TradingDate = "",
    [int]$DayNumber = 1,
    [switch]$ExecuteApprovedLocalSteps
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ScriptPath = Join-Path $RepoRoot "scripts\hqe_final_daily_app_flow_integration_pack.py"

if (-not (Test-Path $PythonExe)) {
    throw "Python venv not found: $PythonExe"
}
if (-not (Test-Path $ScriptPath)) {
    throw "Module 153 script not found: $ScriptPath"
}
if ([string]::IsNullOrWhiteSpace($TradingDate)) {
    $TradingDate = Get-Date -Format "yyyy-MM-dd"
}

$argsList = @(
    $ScriptPath,
    "--repo-root", $RepoRoot,
    "--workspace", $Workspace,
    "--trading-date", $TradingDate,
    "--day-number", "$DayNumber",
    "--write"
)

if ($ExecuteApprovedLocalSteps) {
    $argsList += "--execute-approved-local-steps"
}

& $PythonExe @argsList
