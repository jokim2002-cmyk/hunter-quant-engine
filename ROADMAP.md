# Hunter Quant Engine — Master Roadmap

## Current Status Override - July 2026

This section is the authoritative current HQE state.

Older roadmap sections below are retained as historical planning notes and documentation-test anchors. If an older section says a phase is still planned, this current status section supersedes it.

Current checkpoint:

- 1472 tests passing after Live-readiness gate scaffold.1 release close.1 release close.
- Repository shortcut cleanup completed.
- Old unused/risky root shortcuts removed.
- Safe local shortcut layer completed.
- Paper trading demo/report workflow completed.
- Paper journal persistence skeleton completed.
- Replay journal persistence bridge completed.
- Replay journal demo shortcut completed.
- Replay journal folder shortcut completed.
- Replay journal summary shortcut completed.
- Replay journal all-in-one shortcut completed.
- Replay journal guide completed.
- Replay journal cleanup helper completed.
- Replay journal index completed.
- Replay journal index shortcut completed.
- Replay journal runs viewer completed.
- All-in-one replay journal shortcut uses pretty runs viewer completed.
- Friendly replay journal summary viewer completed.
- Paper MVP v0.1 scope freeze completed.
- Strategy-to-paper bridge completed.
- Backtest evidence runner completed.
- Paper MVP operator workflow completed.
- Paper MVP release gate completed.
- Paper MVP v0.1 release close completed.
- Paper evidence aggregate runner completed.
- Live-readiness gate scaffold completed.
- Replay journal all-in-one shortcut prints index completed.
- Paper P&L is simulation only.
- Real-money execution remains the final phase only.

Current safe local shortcuts:

- `hqe_help.bat`
- `hqe_daily.bat`
- `hqe_quick_check.bat`
- `hqe_test.bat`
- `hqe_status.bat`
- `hqe_snapshot.bat`
- `hqe_paper_demo.bat`
- `hqe_paper_demo_report.bat`
- `hqe_paper_replay_journal.bat`
- `hqe_paper_replay_journal_folder.bat`
- `hqe_paper_replay_journal_summary.bat`
- `hqe_paper_replay_journal_index.bat`
- `hqe_paper_replay_journal_runs.bat`
- `hqe_paper_replay_journal_all.bat`
- `docs/PAPER_TRADING_REPLAY_JOURNAL.md`
- `hqe_paper_report.bat`
- `hqe_paper_report_text.bat`
- `hqe_paper_folder.bat`

Deleted old unused/risky shortcuts:

- `hqe_pull_test.bat`
- `hqe_push.bat`
- `hqe_run_nifty.bat`
- `refresh_fyers_token.bat`

Current next priority:

1. Paper trading live-like replay loop.
2. Paper journal persistence.
3. Paper report/dashboard polish.
4. Real option premium replay strengthening.
5. Broker interface design with mocks only.
6. Live market observer with no orders.
7. Risk gateway.
8. Micro live execution only after paper evidence and risk gateway.

Generated paper report outputs remain local/generated and ignored:

- `reports/paper_trading/report.txt`
- `reports/paper_trading/summary.json`
- `reports/paper_trading/summary.csv`
- `reports/paper_trading/manifest.json`

---


## Corrected Product Direction

HQE first product module is a dynamic NIFTY option-buy planning engine.

Binding rules:

- Signal source: NIFTY spot/index candles.
- Execution target: NIFTY options.
- Bullish signal maps to Call/CE buy planning.
- Bearish signal maps to Put/PE buy planning.
- First module allows option buying only.
- First module does not allow option selling.
- First module does not execute futures or equity trades.
- HQE is not a fixed ATM option buyer.
- Strike selection must be dynamic using option-chain evidence.
- Current SMC benchmark results are underlying signal research only.
- Current SMC benchmark results are not final NIFTY options profitability.

The option-buy module must eventually check:

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

HQE is not a timepass script. It is a serious market research and execution foundation.

## Current Base State

HQE v0.1 Research Engine Foundation:

- Clean Python architecture
- 648 tests passing
- FYERS NIFTY 5m historical data download
- SMC detections: BOS, CHOCH, FVG, Order Blocks, Liquidity, Sweeps
- Strategy config system
- Strict/Balanced/Relaxed strategy modes
- Strategy mode CLI support
- Strategy mode benchmark runner
- PC-only strategy mode benchmark shortcut
- Strategy experiment dry-run runner
- Experiment ranking/report helpers
- PC-only experiment shortcut
- Backtest pipeline
- Trades CSV export
- Equity curve export
- Buy-and-hold benchmark comparison
- Token refresh helper
- PC + Laptop GitHub sync
- Private GitHub repository

Latest completed research checkpoints:

- Latest-zone SMC entry-zone selection added.
- SMC confluence freshness validation added.
- Strict/Balanced/Relaxed modes now produce different behavior.
- Full real-data mode benchmark completed on PC.
- Benchmark outputs remain ignored and Git stays clean after research runs.

Latest benchmark truth after costs:

- Strict: 394 trades, Gross PnL 24,500.00, Charges 55,224.43, Net PnL -30,724.43, HQE Return -307.2443%, Alpha -309.9432%.
- Balanced: 54 trades, Gross PnL 3,000.00, Charges 7,510.19, Net PnL -4,510.19, HQE Return -45.1019%, Alpha -47.8009%.
- Relaxed: 4 trades, Gross PnL 500.00, Charges 426.73, Net PnL 73.27, HQE Return 0.7327%, Alpha -1.9662%.
- Buy & Hold Return: 2.6990%.
- All modes underperformed buy-and-hold after transaction costs.

Important research conclusion:

- Mode separation is achieved.
- Strict mode currently overtrades badly.
- Balanced mode still overtrades after costs.
- Relaxed mode has low trade count and positive net PnL, but still underperforms buy-and-hold.
- Transaction costs dominate high-frequency trade generation.
- No 1-year backtest should be attempted until performance optimization and run-safety controls are added.

This is not a failure. This is honest research output.
HQE must now prioritize diagnostics, performance, and overtrading control before more strategy tuning.

---

## Non-Negotiable Rules

1. No fake profit claims.
2. Every feature must have tests.
3. Every strategy must be benchmarked.
4. Every result must include transaction costs.
5. secrets/ must never be committed.
6. Real-money execution comes last.
7. Broker-specific code must not enter core strategy/backtest logic.
8. UI must show the truth, not hide weak results.
9. Avoid overfitting.
10. No milestone is complete unless tests pass and Git is clean.

---

## Current Machine Workflow

Laptop role:

- Coding
- Unit tests
- Full pytest
- Small sample-data validation
- Git commit and push
- No full real-data mode benchmark runs

PC role:

- Pull latest code
- Full pytest after pull
- Full FYERS real-data backtests
- Strict/Balanced/Relaxed mode benchmark
- Heavy research runs

Reason:

- Laptop shut down during full real-data strategy mode benchmark.
- HQE core is not considered broken or unusable; heavy research runs are PC-only until optimization work is added.

---

## Phase 1 — Strengthen the Research Engine

Goal: Make HQE research-grade before making profit claims.

### 1.1 Strategy Config System

Add configurable settings:

- swing_lookback
- fvg_min_size
- order_block_validity
- liquidity_sweep_threshold
- risk_reward
- stop_buffer
- dedup_window
- session_start
- session_end
- long_enabled
- short_enabled
- trend_filter_enabled

Definition of Done:

- Strategy config dataclass
- Default config backward-compatible
- Tests
- CLI args or config file
- Existing runner still works

### 1.2 More Trade Generation

Current full run produced only 1 trade. We need controlled trade generation.

Work:

- Strict mode
- Balanced mode
- Relaxed mode
- Long side improvement
- De-dup window configurable
- Session filter configurable

Definition of Done:

- Each mode backtested
- Benchmark comparison for each mode
- No fake optimization

### 1.4 Research Safety and Performance Checkpoint

Reason:

- Full mode benchmarks are slow on current architecture.
- Laptop already shut down during full real-data benchmark.
- One-year 5m backtests may be unsafe or too slow without optimization.
- Strict mode overtrading shows that more signals are not automatically better.
- Transaction costs can destroy gross edge.

Work:

- Add benchmark progress logging.
- Add timing summary per strategy mode.
- Add `--max-candles` support for safe partial research runs.
- Add date-range filters for controlled backtests.
- Add conflict diagnostics: bullish-only, bearish-only, both-valid neutral conflict, neither-valid.
- Add trade frequency diagnostics.
- Document when PC-only runs are required.
- Do not tune strategy modes again until diagnostics explain overtrading behavior.

Definition of Done:

- Full benchmark shows progress while running.
- Research scripts can run on limited candle ranges.
- Reports include timing and signal/conflict counts.
- One-year backtest is blocked or warned until safe controls exist.
- Tests pass.
- Git is clean.

### 1.5 Overtrading Control

Reason:

- Strict mode currently generates too many trades.
- Gross PnL can look positive while net PnL is deeply negative after costs.

Work:

- Max trades per day/session.
- Minimum candles between same-direction trades.
- Re-entry cooldown after TP/SL.
- Optional session filter.
- Optional minimum expected reward after charges.
- Trade frequency warnings in reports.

Definition of Done:

- Overtrading controls are configurable.
- Strict/Balanced/Relaxed modes remain benchmarked after costs.
- Reports show gross PnL, charges, and net PnL clearly.
- No fake profit claims.


### 1.3 Baseline Strategy Comparisons

Add comparisons against:

- Buy & Hold
- EMA crossover
- Random entry baseline
- Previous day breakout
- Simple trend-following

Definition of Done:

- Baseline scripts
- Summary CSV
- Benchmark report
- HQE vs all baselines

---

## Phase 2 — Experiment and Optimization Engine

Goal: Let HQE test strategy settings systematically.

### 2.1 Experiment Runner

Script:

- scripts/run_strategy_experiments.py

Current status:

- Dry-run experiment planner built
- strict_default, balanced_default, relaxed_default planned
- `--execute` required for real workflow execution
- Laptop-safe tests added
- Generated experiment outputs ignored
- Experiment result ranking helpers built
- Best/Worst report sections added
- PC-only experiment shortcut added

PC pending:

- Execute experiments on real FYERS data
- Review summary CSV
- Compare net PnL after costs
- Add best/worst config reporting after first PC result

Outputs:

- data/processed/strategy_experiment_summary.csv
- data/processed/strategy_experiment_report.txt
- data/processed/experiments/

Definition of Done:

- Multiple configs run
- Results sorted by net PnL, alpha, drawdown
- Tests
- Report generated

### 2.2 Walk-Forward Testing

Example:

- Train: Jan-Mar, Test: Apr
- Train: Feb-Apr, Test: May
- Train: Mar-May, Test: Jun

Definition of Done:

- Date windows
- In-sample vs out-of-sample report
- No future leakage
- Summary CSV

### 2.3 Anti-Overfitting Rules

Metrics:

- Net PnL
- Alpha vs Buy & Hold
- Max drawdown
- Win rate
- Average trade
- Profit factor
- Trade count
- Robustness score

Definition of Done:

- Config is robust only if it survives multiple periods
- One lucky result is rejected
- Report shows warnings

---

## Phase 3 — Broker-Agnostic Data Layer

Goal: HQE must not be FYERS-bound.

Architecture target:

src/brokers/
- interfaces/
  - historical_data_provider.py
  - live_data_provider.py
  - order_execution_provider.py
  - broker_auth_provider.py
- fyers/
  - fyers_history_provider.py
  - fyers_auth_provider.py
- zerodha/
- upstox/
- angelone/
- dhan/

### 3.1 Broker Interfaces

Common interfaces:

- get_history(symbol, timeframe, from_date, to_date)
- get_latest_candle(symbol)
- subscribe_live(symbols)
- place_order(order)
- cancel_order(order_id)
- get_positions()

Definition of Done:

- Abstract interfaces
- FYERS adapter migrated
- Existing downloader still works
- Tests with mocks

### 3.2 Multi-Broker Historical Data

Adapter order:

1. FYERS
2. Zerodha
3. Upstox
4. Angel One
5. Dhan

Rule:

- No broker code inside strategy/backtest core.

Definition of Done:

- Broker selection via CLI/config
- Same output CSV format
- Broker capability report

---

## Phase 4 — Reports and UI Dashboard

Goal: Move from command line to product experience.

### 4.1 Streamlit Dashboard v1

Features:

- Run backtest button
- Download data button
- Refresh token guide
- Trades table
- Equity curve chart
- Benchmark report
- Latest summary

Definition of Done:

- ui/app.py
- Streamlit runs locally
- No secrets exposed
- Reads generated CSVs
- Tests for helper/config functions

### 4.2 Strategy Experiment Dashboard

Features:

- Select config
- Select date range
- Run experiment
- Compare configs
- Show best/worst settings
- Show alpha vs benchmark

Definition of Done:

- Experiment table
- Equity curve visualization
- Benchmark comparison view

---

## Phase 5 — Live Market Observer

Goal: Live market signals without order placement.

No real orders in this phase.

Script:

- scripts/run_live_market_watch.py

Function:

- Fetch latest candles
- Detect new 5m candle
- Run SMC engine
- Generate signal
- Save signal to CSV
- Show console alert

Output:

timestamp,symbol,timeframe,direction,entry,sl,tp,logic

Definition of Done:

- No order placement
- Live signal log
- Duplicate signal prevention
- Market hours check
- Error handling

---

## Phase 6 — Paper Trading / Forward Testing

Goal: Treat live signals as paper trades.

Features:

- Paper entry
- Paper SL/TP
- Paper exit
- Paper PnL
- Paper charges
- Daily summary

Definition of Done:

- paper_trades.csv
- paper_equity_curve.csv
- live vs backtest comparison
- Minimum 1 month forward test before real money

---

## Phase 7 — Risk Gateway

Goal: Safety wall before real money.

Mandatory controls:

- max_daily_loss
- max_trades_per_day
- max_position_size
- max_capital_exposure
- max_loss_per_trade
- duplicate order prevention
- market close protection
- manual kill switch
- broker failure handling
- paper/live mode separation

Definition of Done:

- RiskManager for live execution
- Kill switch
- Tests for every risk rule
- No broker order can bypass risk gateway

---

## Phase 8 — Micro Live Execution

Goal: Very small quantity/capital real test.

Rules:

- Only after paper trading proof
- Only one broker first
- Only one symbol first
- Only tiny quantity
- Manual kill switch active
- Full logs
- Daily review

Definition of Done:

- Real order placement adapter
- Order log
- Position reconciliation
- Broker error handling
- Daily loss limit

---

## Phase 9 — Multi-Broker Execution

Goal: Broker-agnostic execution engine.

Adapters:

- FYERS
- Zerodha
- Upstox
- Angel One
- Dhan

Definition of Done:

- Same order interface
- Broker-specific conversion isolated
- Capability detection
- Paper/live switch

---

## Phase 10 — Product-Grade HQE

Final polish:

- Installer/setup script
- Documentation
- README.md
- CHANGELOG.md
- Strategy docs
- User guide
- Error guide
- Backup guide
- CI tests
- Release tags

Definition of Done:

- Fresh PC setup documented
- One-command test
- One-command run
- One-command sync
- UI dashboard usable

---

## Immediate Priority Order

1. Roadmap correction for NIFTY option-buy first module - CURRENT
2. README correction for NIFTY option-buy first module - CURRENT
3. Option-buy assumptions document
4. Option contract models
5. Option chain snapshot models
6. FYERS NIFTY options charge profile
7. Dynamic strike selection engine
8. OI / volume / liquidity filters
9. Greeks model and checks
10. Option-buy trade plan model
11. Option premium backtest engine
12. Conflict diagnostics report for underlying SMC signals
13. Overtrading controls
14. Strategy experiment execution on PC
15. Walk-forward testing
16. Streamlit UI dashboard
17. Broker gateway interfaces
18. Live market observer
19. Paper trading
20. Risk gateway
21. Micro live execution

## Completed Checkpoint

### Safe Offline Option Market Data Workflow

Completed:

- Synthetic in-memory recording demo
- CSV validation demo
- CSV replay demo
- End-to-end record -> validate -> replay smoke test

Properties:

- Broker-agnostic
- No FYERS
- No live or real market data
- No orders
- No profitability claim

Relevant paths:

- `examples/record_in_memory_option_market_data.py`
- `examples/validate_option_market_data_csv.py`
- `examples/replay_csv_option_market_data.py`
- `tests/examples/test_option_market_data_demo_workflow.py`
- `docs/OPTION_MARKET_DATA_RECORDING.md`

Future phase:

- Real broker/live data adapter after safety layers

---

## Next Planned Phase: Paper Trading Design and Fake Execution Journal

Next phase after offline data workflow:

- Design first. No paper trading engine is implemented yet.
- Offline/replayed data first. Paper trading must work without a live broker.
- Risk controls before live execution:
  - max trades per day
  - max daily loss
  - max position size
  - cooldown
  - kill switch
- Broker/live execution remains a future phase and must stay isolated from core.
- Real-money execution remains the last phase.

Relevant path:

- `docs/PAPER_TRADING_DESIGN.md`

---

## HQE Philosophy

HQE is not built to show fake profit.

HQE is built to answer honestly:

- What works?
- What fails?
- What survives after costs?
- What beats the benchmark?
- What survives out-of-sample?
- What is safe enough for paper trading?
- What is safe enough for tiny real-money testing?

The goal is not to rush.

The goal is to build something real.


## Paper MVP v0.1 Closure Plan

Paper MVP v0.1 scope is frozen.

Scope docs:

- `docs/PAPER_MVP_V0_1_SCOPE.md`
- `docs/PAPER_MVP_RELEASE_CHECKLIST.md`
- `docs/PAPER_OPERATOR_GUIDE.md`
- `docs/PAPER_MVP_V0_1_RELEASE_NOTES.md`
- `docs/LIVE_READINESS_GATE.md`
- `hqe_paper_mvp_release_check.bat`
- `docs/DEFERRED_POLISH_BACKLOG.md`

Only these items can block Paper MVP v0.1:

No remaining code/documentation blockers before the Paper MVP v0.1 release tag.

Deferred beyond v0.1:

- live broker execution
- real-money trading
- dashboard polish
- cosmetic shortcut/docs polish
- profitability claims without evidence
