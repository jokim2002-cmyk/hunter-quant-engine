param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$Now = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ScriptPath = Join-Path $RepoRoot "scripts\hqe_market_session_supervisor.py"

if ($Now -eq "") {
  & $PythonExe $ScriptPath --workspace $Workspace --write
} else {
  & $PythonExe $ScriptPath --workspace $Workspace --now $Now --write
}

