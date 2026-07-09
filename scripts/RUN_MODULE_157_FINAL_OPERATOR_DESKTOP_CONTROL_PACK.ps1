param(
    [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
    [string]$TradingDate = "2026-07-09",
    [int]$DayNumber = 1,
    [switch]$GuardCheck
)

$ErrorActionPreference = "Stop"
Set-Location "D:\Hunter_Quant_Engine_PC_TRANSFER"
$PythonExe = ".\.venv\Scripts\python.exe"

if ($GuardCheck) {
    & $PythonExe "scripts\hqe_final_operator_desktop_control_pack.py" --guard-check
    exit $LASTEXITCODE
}

& $PythonExe "scripts\hqe_final_operator_desktop_control_pack.py" --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --write
exit $LASTEXITCODE
