# Hunter Quant Engine (HQE)

## Mission Statement

Build a production-grade NIFTY option-buy research and execution foundation using clean architecture, rigorous testing, explainable logic, and honest benchmark results.

HQE is not a fake-profit trading bot.

HQE is a market research and execution framework designed to transform NIFTY spot/index data into strategy signals, option-chain analysis, CE/PE buy trade plans, backtest results, benchmark reports, and eventually paper/live execution decisions.

---

## Corrected First Module Direction

HQE first product module is a dynamic NIFTY option-buy planning engine.

Binding rules:

- Signal source: NIFTY spot/index candles.
- Execution target: NIFTY options.
- Bullish signal maps to Call/CE buy planning.
- Bearish signal maps to Put/PE buy planning.
- Option buying only.
- No option selling in the first module.
- No futures execution in the first module.
- No equity execution in the first module.
- No fixed ATM-only assumption.
- Strike selection must be dynamic.
- Current SMC mode benchmarks are underlying signal research only.
- Current SMC mode benchmarks are not final NIFTY options profitability.

The final option-buy planning module must check:

- Strike selection.
- Expiry.
- Option premium.
- OI.
- Volume.
- Liquidity/spread.
- Delta.
- Theta.
- Vega.
- Gamma.
- Risk-reward.
- SL and target.
- FYERS NIFTY options charges.

---

## Project Motto

Engineer it right once. Improve it forever.

---

## Current Status

HQE currently supports:

- Clean Python architecture
- 1339 tests passing
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
- Safe local paper trading demo CLI
- Local paper report bundle generation

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

Shortcut quick-start card: `README_SHORTCUTS.md`

Run the safe local paper trading demo CLI:

    .\.venv\Scripts\python.exe -m src.paper_trading.paper_trading_demo_cli

Run the safe local paper trading demo example wrapper:

    .\.venv\Scripts\python.exe examples\run_paper_trading_demo.py

Paper demo shortcuts:

    .\hqe_paper_demo.bat
    .\hqe_paper_report.bat
    .\hqe_paper_demo_report.bat
    .\hqe_paper_folder.bat

Run the full test suite shortcut:

    .\hqe_test.bat

Show safe local shortcuts:

    .\hqe_help.bat

Run quick local check shortcut:

    .\hqe_quick_check.bat
    .\hqe_daily.bat

Check Git status shortcut:

    .\hqe_status.bat
    .\hqe_snapshot.bat

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

Immediate engineering milestones:

- Roadmap and README correction for NIFTY option-buy direction.
- Option-buy assumptions document.
- Option contract models.
- Option chain snapshot models.
- FYERS NIFTY options charge profile.
- Dynamic strike selection engine.
- OI / volume / liquidity filters.
- Greeks model and checks.
- Option-buy trade plan model.
- Option premium backtest engine.

Current SMC strict/balanced/relaxed benchmarks remain useful as underlying signal research, but they are not final NIFTY options profitability results.

---

## Documentation

- ROADMAP.md
- docs/PC_BENCHMARK_RUNBOOK.md
- docs/PAPER_TRADING_DESIGN.md
- docs/PAPER_TRADING_DEMO_CLI.md
- docs/OPTION_MARKET_DATA_RECORDING.md

## Safe Local Paper Trading Demo CLI

HQE now has a safe local paper trading demo CLI.

Run it from the project root:

    .\.venv\Scripts\python.exe -m src.paper_trading.paper_trading_demo_cli

The example wrapper also works:

    .\.venv\Scripts\python.exe examples\run_paper_trading_demo.py

The CLI:

- Uses a synthetic approved NIFTY CE option-buy trade plan.
- Submits and closes a fake local paper position.
- Shows paper-only simulated gross P&L, estimated costs, and simulated net P&L.
- Cleans known generated report bundle files before writing fresh reports.
- Writes local report files under reports/paper_trading/.
- Does not use FYERS.
- Does not use live or real market data.
- Does not place real orders.
- Is not a profitability claim.

Detailed guide:

- docs/PAPER_TRADING_DEMO_CLI.md

## Safe Offline Option Market Data Workflow

HQE now has a completed broker-agnostic offline option market data workflow.

It covers:

- Synthetic in-memory recording demo
- CSV validation demo
- CSV replay demo
- End-to-end record -> validate -> replay smoke test

This workflow:

- Is broker-agnostic
- Does not use FYERS
- Does not use live or real market data
- Does not place orders
- Is not a profitability claim

Relevant paths:

- `examples/record_in_memory_option_market_data.py`
- `examples/validate_option_market_data_csv.py`
- `examples/replay_csv_option_market_data.py`
- `tests/examples/test_option_market_data_demo_workflow.py`
- `docs/OPTION_MARKET_DATA_RECORDING.md`

Real broker/live market data remains a future phase.

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
