param(
    [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
    [string]$TradingDate = "",
    [int]$DayNumber = 1
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if ($TradingDate -eq "") {
    & $Py "scripts\hqe_paper_signal_no_trade_reason_engine.py" --workspace $Workspace --day-number $DayNumber --write
} else {
    & $Py "scripts\hqe_paper_signal_no_trade_reason_engine.py" --workspace $Workspace --trading-date $TradingDate --day-number $DayNumber --write
}
