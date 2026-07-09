param(
    [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ScriptPath = Join-Path $RepoRoot "scripts\hqe_final_paper_validation_master_handoff_freeze_pack.py"

& $PythonExe $ScriptPath --workspace $Workspace --write
