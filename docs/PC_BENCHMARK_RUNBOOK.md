# PC Benchmark Runbook

This guide is for running heavy HQE real-data benchmarks on the PC.

Do not run full real-data strategy mode benchmarks on the laptop.

## Machine Rule

Laptop:

- Code changes
- Unit tests
- Full pytest with py -m pytest
- Small sample-data validation
- Git commit and push

PC:

- Pull latest code
- Full pytest after pull
- Full FYERS real-data benchmark
- Heavy research runs

## PC Steps

Open PowerShell on PC:

cd /d "D:\Hunter_Quant_Engine_PC_TRANSFER"
git status --short
git pull --ff-only
.\.venv\Scripts\python.exe -m pytest
.\hqe_benchmark_modes.bat

Direct benchmark command:

.\.venv\Scripts\python.exe scripts\benchmark_strategy_modes.py --input "data\raw\fyers_nifty_5min.csv"

## Output Files

Report:
data\processed\fyers_nifty_5m_mode_benchmark_report.txt

Summary:
data\processed\fyers_nifty_5m_mode_benchmark_summary.csv

Read outputs:

Get-Content "data\processed\fyers_nifty_5m_mode_benchmark_report.txt"
Get-Content "data\processed\fyers_nifty_5m_mode_benchmark_summary.csv"
git status --short

## Commit Rule

Generated benchmark output files must not be committed.

Ignored generated outputs:

data/processed/fyers_nifty_5m_strict_*
data/processed/fyers_nifty_5m_balanced_*
data/processed/fyers_nifty_5m_relaxed_*
data/processed/*mode_benchmark*

## Result Rule

Do not judge HQE from gross PnL only.

Judge using:

- net PnL after costs
- return percent
- alpha vs buy-and-hold
- trade count
- charges
- mode robustness

No fake profit claims.
