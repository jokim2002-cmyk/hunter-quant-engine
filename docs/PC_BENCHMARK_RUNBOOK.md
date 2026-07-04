# PC Benchmark Runbook

This guide is for running heavy HQE real-data benchmarks and experiments on the PC.

Do not run full real-data strategy mode benchmarks or experiment execution on the laptop.

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
- Full strategy experiment execution
- Heavy research runs

## PC Setup Steps

Open PowerShell on PC:

cd /d "D:\Hunter_Quant_Engine_PC_TRANSFER"
git status --short
git pull --ff-only
.\.venv\Scripts\python.exe -m pytest

## Run Strategy Mode Benchmark

Preferred shortcut:

.\hqe_benchmark_modes.bat

Direct command:

.\.venv\Scripts\python.exe scripts\benchmark_strategy_modes.py --input "data\raw\fyers_nifty_5min.csv"

Benchmark report:

data\processed\fyers_nifty_5m_mode_benchmark_report.txt

Benchmark summary:

data\processed\fyers_nifty_5m_mode_benchmark_summary.csv

## Run Strategy Experiments

Preferred shortcut:

.\hqe_run_experiments.bat

Direct command:

.\.venv\Scripts\python.exe scripts\run_strategy_experiments.py --execute --input "data\raw\fyers_nifty_5min.csv"

Experiment report:

data\processed\strategy_experiment_report.txt

Experiment summary:

data\processed\strategy_experiment_summary.csv

Experiment files:

data\processed\experiments\

## Read Outputs

Get-Content "data\processed\fyers_nifty_5m_mode_benchmark_report.txt"
Get-Content "data\processed\fyers_nifty_5m_mode_benchmark_summary.csv"
Get-Content "data\processed\strategy_experiment_report.txt"
Get-Content "data\processed\strategy_experiment_summary.csv"
git status --short

## Commit Rule

Generated benchmark and experiment output files must not be committed.

Ignored generated outputs:

data/processed/fyers_nifty_5m_strict_*
data/processed/fyers_nifty_5m_balanced_*
data/processed/fyers_nifty_5m_relaxed_*
data/processed/*mode_benchmark*
data/processed/experiments/
data/processed/strategy_experiment_report.txt
data/processed/strategy_experiment_summary.csv

## Result Rule

Do not judge HQE from gross PnL only.

Judge using:

- net PnL after costs
- return percent
- alpha vs buy-and-hold
- trade count
- charges
- mode robustness
- best/worst experiment rankings

No fake profit claims.
