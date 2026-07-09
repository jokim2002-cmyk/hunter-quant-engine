param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [switch]$RequireEnv,
  [switch]$Write
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"

$ArgsList = @(
  "scripts\hqe_fyers_data_only_connector.py",
  "--preflight",
  "--workspace",
  $Workspace
)

if ($RequireEnv) {
  $ArgsList += "--require-env"
}

if ($Write) {
  $ArgsList += "--write"
}

& $Py @ArgsList
