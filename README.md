# Hunter Quant Engine (HQE)

## Mission Statement

Build a production-grade NIFTY option-buy research and execution foundation using clean architecture, rigorous testing, explainable logic, and honest benchmark results.

HQE is not a fake-profit trading bot.

HQE is a market research and execution framework designed to transform NIFTY spot/index data into strategy signals, option-chain analysis, CE/PE buy trade plans, backtest results, benchmark reports, and eventually paper/live execution decisions.

---


## Paper MVP v0.1 Scope Freeze

HQE is now using a frozen Paper MVP v0.1 scope to avoid infinite micro-polish.

Paper MVP v0.1 is paper-only:

- no broker orders
- no real-money trading
- no live execution
- no profitability claim

Roadmap-closing work now happens in larger module patches with tests and full
quick-check validation.

Module B added the Strategy-to-paper bridge for approved option-buy plans.
Module C added the Backtest evidence runner for paper pass/fail gates.
Module D added the Paper MVP operator demo and operator guide.
Module E added the Paper MVP release gate.
Module F added Paper MVP v0.1 release notes and release-close prep.
Module G added the Paper evidence aggregate runner.
Module H added the Live-readiness gate scaffold.
Module I added the disabled live safety lock scaffold.
Module J added the full live-readiness preflight.
Module K added the deny-only live execution firewall.
Module L integrated the live execution firewall into the preflight.
Module M added v0.2 live-readiness scaffold release notes.
Module N added the recorded-data evidence inventory.

Key scope documents:

- `docs/PAPER_MVP_V0_1_SCOPE.md`
- `docs/PAPER_MVP_RELEASE_CHECKLIST.md`
- `docs/PAPER_OPERATOR_GUIDE.md`
- `docs/PAPER_MVP_V0_1_RELEASE_NOTES.md`
- `docs/LIVE_READINESS_GATE.md`
- `docs/LIVE_SAFETY_LOCK.md`
- `docs/LIVE_READINESS_PREFLIGHT.md`
- `docs/LIVE_EXECUTION_FIREWALL.md`
- `docs/LIVE_READINESS_SCAFFOLD_V0_2_RELEASE_NOTES.md`
- `docs/RECORDED_DATA_EVIDENCE_INVENTORY.md`
- `hqe_paper_mvp_release_check.bat`
- `docs/DEFERRED_POLISH_BACKLOG.md`

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
- 1530 tests passing
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
    .\hqe_paper_report_text.bat

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
- `docs/PAPER_TRADING_REPLAY_JOURNAL.md`
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

## Module O - Recorded data replay dataset normalizer

Shortcut:

.\hqe_recorded_data_replay_dataset.bat

This paper/simulation-only evidence module reads the recorded-data inventory output and/or discovered files under data\recorded and data\live_recording, then writes normalized replay dataset reports under reports\paper_trading\recorded_data_replay_dataset.

It safely parses simple CSV, JSON, and JSONL samples into timestamp/open/high/low/close/volume fields when available. Parquet discovery is tracked but parsing is intentionally deferred in this scaffold.

This module does not connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module P - Recorded data replay quality gate

Shortcut:

.\hqe_recorded_data_replay_quality_gate.bat

This paper/simulation-only evidence module audits the normalized replay dataset from Module O and writes quality-gate reports under reports\paper_trading\recorded_data_replay_quality_gate.

It checks dataset shape, required timestamp/open/high/low/close fields, OHLC sanity, negative volume, duplicate replay rows, timestamp ordering, source parse errors, and skipped rows.

This module does not connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module Q - Recorded data replay dry-run player

Shortcut:

.\hqe_recorded_data_replay_dry_run.bat

This paper/simulation-only evidence module converts the normalized recorded-data replay dataset into a deterministic dry-run event stream under reports\paper_trading\recorded_data_replay_dry_run.

It reads the replay dataset and the replay quality gate output, blocks event generation when the quality gate has failed, and writes dry-run report, event JSONL, and manifest files.

This module does not run strategies, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module R - Recorded data replay evidence bundle

Shortcut:

.\hqe_recorded_data_replay_evidence.bat

This paper/simulation-only evidence module runs the recorded-data replay readiness pipeline end to end: dataset normalizer, quality gate, dry-run player, and combined evidence summary.

It writes the combined bundle under reports\paper_trading\recorded_data_replay_evidence while preserving stage outputs under reports\paper_trading.

This module does not run strategies, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module S - Recorded data replay acceptance gate

Shortcut:

.\hqe_recorded_data_replay_acceptance.bat

This paper/simulation-only evidence module reads the combined recorded-data replay evidence summary from Module R and gates whether it is structurally acceptable for a future paper strategy replay phase.

It checks required stage presence, stage status, bundle status, warning policy, and minimum replay dry-run event count.

This module does not run strategies, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module T - Recorded data replay readiness gate

Shortcut:

.\hqe_recorded_data_replay_readiness.bat

This paper/simulation-only evidence module runs the recorded-data replay evidence bundle and acceptance gate, then writes a final readiness report for future paper replay.

It checks structural replay readiness only. It does not run strategies, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module U - Recorded data strategy input contract

Shortcut:

.\hqe_recorded_data_strategy_input_contract.bat

This paper/simulation-only evidence module converts recorded-data replay dry-run events into structurally safe input bars for a future paper strategy replay phase.

It checks JSONL event shape, required timestamp/close fields, expected recorded market-data bar event type, minimum accepted bar count, and blocks execution/trading/profit fields from entering the contract.

This module does not run strategies, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module V - Recorded data strategy replay preflight

Shortcut:

.\hqe_recorded_data_strategy_replay_preflight.bat

This paper/simulation-only evidence module runs recorded-data replay readiness plus the recorded-data strategy input contract, then writes a final preflight report for a future paper strategy replay phase.

It checks structural readiness only. It does not run strategies, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module W - Recorded data strategy replay scenario manifest

Shortcut:

.\hqe_recorded_data_strategy_replay_scenario.bat

This paper/simulation-only evidence module packages recorded-data strategy input bars into deterministic future paper replay scenarios grouped by recorded source file.

It checks the strategy input bars, preflight readiness, paper-only execution mode, and minimum bars per scenario. It does not run strategies, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module X - Recorded data strategy replay scenario acceptance gate

Shortcut:

.\hqe_recorded_data_strategy_replay_scenario_acceptance.bat

This paper/simulation-only evidence module reads the recorded-data strategy replay scenario manifest and gates whether it is structurally acceptable for a future paper strategy replay phase.

It checks scenario manifest status, minimum scenario count, minimum bars per scenario, required scenario fields, recorded_replay data mode, and paper_simulation_only execution mode.

This module does not run strategies, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## Module Y - Recorded data strategy replay scenario readiness gate

Shortcut:

.\hqe_recorded_data_strategy_replay_scenario_readiness.bat

This paper/simulation-only evidence module runs the recorded-data strategy replay preflight, scenario manifest, and scenario acceptance gate, then writes a final scenario readiness report for a future paper strategy replay phase.

It checks structural scenario readiness only. It does not run strategies, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

## v0.3 - Recorded data replay readiness release

Tag: v0.3-recorded-data-replay-readiness

This paper/simulation-only release closes the recorded-data replay readiness phase from inventory through scenario readiness.

Main command:

.\hqe_recorded_data_strategy_replay_scenario_readiness.bat

The release does not run strategies, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, or prove profitability. This is not a profitability claim.

Release notes:

docs\V0_3_RECORDED_DATA_REPLAY_READINESS_RELEASE.md

## Module AA - Recorded data paper strategy replay plan scaffold

Shortcut:

.\hqe_recorded_data_paper_strategy_replay_plan.bat

This paper/simulation-only evidence module builds a no-execution replay plan from scenario readiness, scenario manifest, and strategy input bars.

It does not run strategies, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, calculate PnL, or prove profitability. This is not a profitability claim.

## Module BB - Recorded data paper strategy replay plan acceptance gate

Shortcut:

.\hqe_recorded_data_paper_strategy_replay_plan_acceptance.bat

This paper/simulation-only evidence module gates the no-execution replay plan from Module AA.

It checks replay plan status, readiness, minimum scenario plans, minimum total planned bars, no-execution modes, broker-disabled mode, manifest-only output mode, and blocks execution/trading/profit fields.

It does not run strategies, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, calculate PnL, or prove profitability. This is not a profitability claim.

## Module CC - Recorded data paper strategy replay plan readiness gate

Shortcut:

.\hqe_recorded_data_paper_strategy_replay_plan_readiness.bat

This paper/simulation-only evidence module runs the no-execution replay plan plus replay-plan acceptance gate, then writes a final plan readiness report.

It does not run strategies, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, calculate PnL, or prove profitability. This is not a profitability claim.

## Module DD - Recorded data paper strategy adapter contract

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_contract.bat

This paper/simulation-only evidence module converts an accepted replay plan into adapter request manifests for a future paper strategy adapter.

It does not execute strategy logic, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, calculate PnL, or prove profitability. This is not a profitability claim.

## Module EE - Recorded data paper strategy adapter contract acceptance gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_contract_acceptance.bat

This paper/simulation-only evidence module gates the adapter contract from Module DD before any future adapter dry-run consumer can use it.

It does not execute strategy logic, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, calculate PnL, or prove profitability. This is not a profitability claim.

## Module FF - Recorded data paper strategy adapter readiness gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_readiness.bat

This paper/simulation-only evidence module runs the adapter contract plus adapter contract acceptance gate, then writes final adapter readiness for a future adapter dry-run phase.

It does not execute strategy logic, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, calculate PnL, or prove profitability. This is not a profitability claim.

## Module GG - Recorded data paper strategy adapter dry-run scaffold

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run.bat

This paper/simulation-only evidence module converts adapter requests into deterministic dry-run events for a future adapter phase.

It does not execute strategy logic, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, calculate PnL, or prove profitability. This is not a profitability claim.
