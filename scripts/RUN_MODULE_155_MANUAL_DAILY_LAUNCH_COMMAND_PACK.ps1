$ErrorActionPreference = 'Stop'
Set-Location "D:\Hunter_Quant_Engine_PC_TRANSFER"

$workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"
$tradingDate = "2026-07-09"
$dayNumber = 1
$py = ".\.venv\Scripts\python.exe"

& $py scripts\hqe_manual_daily_launch_command_pack.py --workspace $workspace --trading-date $tradingDate --day-number $dayNumber --write
& $py scripts\hqe_manual_daily_launch_command_pack.py --guard-check
