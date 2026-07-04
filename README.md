# Hunter Quant Engine (HQE)

## Mission Statement

Build a production-grade quantitative trading research and execution foundation using clean architecture, rigorous testing, explainable logic, and honest benchmark results.

HQE is not a fake-profit trading bot.

HQE is a market research and execution framework designed to transform market data into immutable market events, strategy signals, risk-approved trade plans, backtest results, benchmark reports, and eventually paper/live execution decisions.

---

## Project Motto

Engineer it right once. Improve it forever.

---

## Current Status

HQE currently supports:

- Clean Python architecture
- 616 tests passing
- Smart Money Concepts detection
- SMC strategy signal generation
- Strategy config presets
- Strict/Balanced/Relaxed strategy modes
- Strategy mode CLI support
- Backtest pipeline
- Trade CSV export
- Net equity curve export
- Transaction cost modeling
- Buy-and-hold benchmark comparison
- Strategy mode benchmark runner
- Strategy experiment dry-run planner
- Experiment result ranking helpers
- PC-only benchmark and experiment shortcuts
- PC + laptop GitHub workflow

Current benchmark truth:

- First real FYERS NIFTY baseline underperformed buy-and-hold
- This is not treated as failure
- It is treated as the first honest baseline
- Future work must improve based on net results after costs

---

## Machine Workflow

Laptop role:

- Code changes
- Unit tests
- Full pytest
- Small sample-data validation
- Git commit and push

PC role:

- Pull latest code
- Full pytest after pull
- Full FYERS real-data benchmarks
- Strategy mode benchmark execution
- Strategy experiment execution
- Heavy research runs

Do not run full real-data strategy mode benchmarks or experiment execution on the laptop.

---

## Safe Laptop Commands

Run all tests:

```powershell
py -m pytest
```

Run experiment dry-run only:

```powershell
py scripts\run_strategy_experiments.py
```

Check Git status:

```powershell
git status --short
```

---

## PC-Only Heavy Commands

Strategy mode benchmark:

```powershell
.\hqe_benchmark_modes.bat
```

Strategy experiment execution:

```powershell
.\hqe_run_experiments.bat
```

Direct strategy mode benchmark command:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_strategy_modes.py --input "data\raw\fyers_nifty_5min.csv"
```

Direct strategy experiment command:

```powershell
.\.venv\Scripts\python.exe scripts\run_strategy_experiments.py --execute --input "data\raw\fyers_nifty_5min.csv"
```

---

## Architecture

```text
Market Data
    |
    v
Detection Layer
    |
    v
Immutable Market Events
    |
    v
StrategyContext
    |
    v
Rules and Rule Sets
    |
    v
Setup Validators
    |
    v
Strategies
    |
    v
TradeSignal
    |
    v
Risk Layer
    |
    v
TradePlan
    |
    v
Backtesting / Benchmarking / Experiments
    |
    v
Paper Trading / Live Trading
```

---

## Completed Layers

### Detection Layer

- Candle
- Swing Detection
- Market Structure
- BOS
- CHOCH
- Liquidity
- Equal High
- Equal Low
- Liquidity Clusters
- Liquidity Sweep
- Fair Value Gap
- Order Block

### Strategy Layer

- SignalType
- SignalStrength
- TradeSignal
- StrategyContext
- BaseStrategy
- BaseRule
- Market Structure Rules
- Liquidity Rules
- Fair Value Gap Rules
- Order Block Rules
- Rule Sets
- Setup Validators
- SMCStrategy
- SMCStrategyConfig
- Strict/Balanced/Relaxed modes

### Risk and Backtest Layer

- RiskProfile
- TradePlan
- TradeLevels
- FixedRiskPositionSizer
- FixedRewardToRiskTradeLevelPlanner
- RiskManager
- Backtest pipeline
- Transaction cost model
- Trade CSV export
- Net equity curve export

### Research Layer

- Buy-and-hold benchmark comparison
- Strategy mode benchmark runner
- Strategy experiment dry-run planner
- Experiment result sorting
- Best/worst experiment ranking sections

---

## Non-Negotiable Rules

1. No fake profit claims.
2. Every feature must have tests.
3. Every strategy must be benchmarked.
4. Every result must include transaction costs.
5. secrets/ must never be committed.
6. Real-money execution comes last.
7. Broker-specific code must stay isolated from core strategy/backtest logic.
8. UI must show truth, not hide weak results.
9. Avoid overfitting.
10. No milestone is complete unless tests pass and Git is clean.

---

## Current Priority

Immediate PC pending work:

- Pull latest code on PC
- Run full tests on PC
- Run strict/balanced/relaxed strategy mode benchmark
- Run strategy experiment execution
- Review net PnL after costs
- Compare against buy-and-hold

Next engineering milestones:

- Full experiment execution review
- Walk-forward testing
- Streamlit UI dashboard
- Broker gateway interfaces
- Live market observer
- Paper trading
- Risk gateway
- Micro live execution

---

## Documentation

- ROADMAP.md
- docs/PC_BENCHMARK_RUNBOOK.md

---

## Guiding Principle

Every release should improve truth, safety, and quality without sacrificing simplicity.

HQE is built to answer honestly:

- What works?
- What fails?
- What survives after costs?
- What beats the benchmark?
- What survives out-of-sample?
- What is safe enough for paper trading?
- What is safe enough for tiny real-money testing?
