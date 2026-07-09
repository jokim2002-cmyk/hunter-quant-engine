param(
    [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
    [string]$UserId = "jokim-local",
    [switch]$LaunchGui
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if ($LaunchGui) {
    & $PythonExe "scripts\hqe_local_visual_dashboard_app.py" --launch-gui --workspace $Workspace --user-id $UserId
} else {
    & $PythonExe "scripts\hqe_local_visual_dashboard_app.py" --workspace $Workspace --user-id $UserId --write
}
