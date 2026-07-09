param(
    [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"
)

$ErrorActionPreference = "Stop"
$Repo = (Get-Location).Path
$Py = Join-Path $Repo ".venv\Scripts\python.exe"
$Script = Join-Path $Repo "scripts\hqe_pc_startup_auto_open_scheduler.py"

if (!(Test-Path $Py)) { throw "Python venv not found: $Py" }
if (!(Test-Path $Script)) { throw "Module 152 script not found: $Script" }

& $Py $Script --workspace $Workspace --repo $Repo --write
& $Py $Script --guard-check
