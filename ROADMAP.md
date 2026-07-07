# Hunter Quant Engine — Master Roadmap

## Current Status Override - July 2026

This section is the authoritative current HQE state.

Older roadmap sections below are retained as historical planning notes and documentation-test anchors. If an older section says a phase is still planned, this current status section supersedes it.

Current checkpoint:

- 1530 tests passing after Recorded-data evidence inventory.2 live-readiness scaffold release notes.1 release close.1 release close.
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
- Live safety lock scaffold completed.
- Live-readiness preflight completed.
- Live execution firewall scaffold completed.
- Preflight firewall integration completed.
- v0.2 live-readiness scaffold release notes completed.
- Recorded-data evidence inventory completed.
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
- `docs/LIVE_SAFETY_LOCK.md`
- `docs/LIVE_READINESS_PREFLIGHT.md`
- `docs/LIVE_EXECUTION_FIREWALL.md`
- `docs/LIVE_READINESS_SCAFFOLD_V0_2_RELEASE_NOTES.md`
- `docs/RECORDED_DATA_EVIDENCE_INVENTORY.md`
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

## Module O - Recorded data replay dataset normalizer

Status: implemented in this module.

Scope:
- Read recorded-data inventory output when available.
- Fall back to discovery under data\recorded and data\live_recording.
- Normalize simple CSV/JSON/JSONL rows into replay records with timestamp/open/high/low/close/volume when available.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_replay_dataset.
- Add shortcut .\hqe_recorded_data_replay_dataset.bat.
- Keep broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module O: 1546 passed.

## Module P - Recorded data replay quality gate

Status: implemented in this module.

Scope:
- Read the normalized replay dataset from reports\paper_trading\recorded_data_replay_dataset\dataset.json.
- Audit dataset JSON shape and replay record availability.
- Flag missing timestamp/open/high/low/close fields.
- Flag invalid OHLC relationships and negative volume.
- Warn on duplicate replay rows and out-of-order parseable timestamps.
- Surface source parse errors, skipped rows, and skipped sources.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_replay_quality_gate.
- Add shortcut .\hqe_recorded_data_replay_quality_gate.bat.
- Keep broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module P: 1560 passed.

## Module Q - Recorded data replay dry-run player

Status: implemented in this module.

Scope:
- Read the normalized replay dataset from reports\paper_trading\recorded_data_replay_dataset\dataset.json.
- Read the replay quality gate from reports\paper_trading\recorded_data_replay_quality_gate\quality_gate.json.
- Block dry-run event generation if the replay quality gate status is fail.
- Convert playable replay records into deterministic paper/simulation event JSONL.
- Skip unplayable records missing timestamp or close and report them.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_replay_dry_run.
- Add shortcut .\hqe_recorded_data_replay_dry_run.bat.
- Keep strategy execution, trade plans, broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module Q: 1574 passed.

## Module R - Recorded data replay evidence bundle

Status: implemented in this module.

Scope:
- Run the recorded-data replay dataset normalizer.
- Run the recorded-data replay quality gate.
- Run the recorded-data replay dry-run player.
- Write a combined evidence summary and manifest.
- Add shortcut .\hqe_recorded_data_replay_evidence.bat.
- Keep strategy execution, trade plans, broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module R: 1587 passed.

## Module S - Recorded data replay acceptance gate

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_replay_evidence\evidence_summary.json.
- Verify required replay evidence stages are present.
- Gate stage status and bundle status.
- Enforce configurable minimum replay dry-run event count.
- Add optional warning acceptance via --allow-warnings.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_replay_acceptance.
- Add shortcut .\hqe_recorded_data_replay_acceptance.bat.
- Keep strategy execution, trade plans, broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module S: 1599 passed.

## Module T - Recorded data replay readiness gate

Status: implemented in this module.

Scope:
- Run the recorded-data replay evidence bundle.
- Run the recorded-data replay acceptance gate.
- Write final readiness report under reports\paper_trading\recorded_data_replay_readiness.
- Add shortcut .\hqe_recorded_data_replay_readiness.bat.
- Keep strategy execution, trade plans, broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module T: 1611 passed.

## Module U - Recorded data strategy input contract

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_replay_dry_run\dry_run_events.jsonl.
- Convert safe recorded_market_data_bar events into strategy input bars.
- Enforce timestamp and close as required fields.
- Reject execution/trading/profit fields from the input contract.
- Enforce configurable minimum accepted bar count.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_strategy_input_contract.
- Add shortcut .\hqe_recorded_data_strategy_input_contract.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module U: 1623 passed.

## Module V - Recorded data strategy replay preflight

Status: implemented in this module.

Scope:
- Run the recorded-data replay readiness gate.
- Run the recorded-data strategy input contract.
- Write final preflight report under reports\paper_trading\recorded_data_strategy_replay_preflight.
- Add shortcut .\hqe_recorded_data_strategy_replay_preflight.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module V: 1634 passed.

## Module W - Recorded data strategy replay scenario manifest

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_strategy_input_contract\strategy_input_bars.jsonl.
- Read reports\paper_trading\recorded_data_strategy_replay_preflight\preflight_report.json.
- Group accepted bars into deterministic replay scenarios by source file.
- Enforce configurable minimum bars per scenario.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_strategy_replay_scenario.
- Add shortcut .\hqe_recorded_data_strategy_replay_scenario.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module W: 1645 passed.

## Module X - Recorded data strategy replay scenario acceptance gate

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_strategy_replay_scenario\scenario_manifest.json.
- Gate scenario manifest status and warning policy.
- Enforce configurable minimum scenario count.
- Enforce configurable minimum bars per scenario.
- Verify scenario identity/source/timestamp fields.
- Verify recorded_replay and paper_simulation_only modes.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_strategy_replay_scenario_acceptance.
- Add shortcut .\hqe_recorded_data_strategy_replay_scenario_acceptance.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module X: 1657 passed.

## Module Y - Recorded data strategy replay scenario readiness gate

Status: implemented in this module.

Scope:
- Run the recorded-data strategy replay preflight.
- Run the recorded-data strategy replay scenario manifest.
- Run the recorded-data strategy replay scenario acceptance gate.
- Write final scenario readiness report under reports\paper_trading\recorded_data_strategy_replay_scenario_readiness.
- Add shortcut .\hqe_recorded_data_strategy_replay_scenario_readiness.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Expected full quick-check suite after Module Y: 1668 passed.

## Module Z - v0.3 recorded-data replay readiness release close

Status: implemented in this module.

Release tag:
v0.3-recorded-data-replay-readiness

Scope:
- Add v0.3 recorded-data replay readiness release notes.
- Document Modules N through Y as a paper/simulation-only evidence release.
- Confirm the main scenario readiness shortcut: .\hqe_recorded_data_strategy_replay_scenario_readiness.bat.
- Preserve no broker, no live market data, no real orders, no real money, no strategy execution, no signal generation, no trade plans, and no profitability claim boundaries.
- Create release tag v0.3-recorded-data-replay-readiness after green checks and commit.

Expected full quick-check suite after Module Z: 1676 passed.

## Module AA - Recorded data paper strategy replay plan scaffold

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_strategy_replay_scenario_readiness\scenario_readiness_report.json.
- Read reports\paper_trading\recorded_data_strategy_replay_scenario\scenario_manifest.json.
- Read reports\paper_trading\recorded_data_strategy_input_contract\strategy_input_bars.jsonl.
- Build deterministic no-execution replay scenario plans.
- Block execution/profit fields from the plan.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_paper_strategy_replay_plan.
- Add shortcut .\hqe_recorded_data_paper_strategy_replay_plan.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module AA: 1687 passed.

## Module BB - Recorded data paper strategy replay plan acceptance gate

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_paper_strategy_replay_plan\paper_strategy_replay_plan.json.
- Gate replay plan status and ready_to_plan flag.
- Enforce configurable minimum scenario plans.
- Enforce configurable minimum total planned bars.
- Verify no-execution strategy mode, broker-disabled mode, and manifest-only output mode.
- Block execution/trading/profit fields from the plan.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_paper_strategy_replay_plan_acceptance.
- Add shortcut .\hqe_recorded_data_paper_strategy_replay_plan_acceptance.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module BB: 1699 passed.

## Module CC - Recorded data paper strategy replay plan readiness gate

Status: implemented in this module.

Scope:
- Run the recorded-data paper strategy replay plan scaffold.
- Run the recorded-data paper strategy replay plan acceptance gate.
- Write final plan readiness report under reports\paper_trading\recorded_data_paper_strategy_replay_plan_readiness.
- Add shortcut .\hqe_recorded_data_paper_strategy_replay_plan_readiness.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module CC: 1710 passed.

## Module DD - Recorded data paper strategy adapter contract

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_paper_strategy_replay_plan_readiness\paper_strategy_replay_plan_readiness.json.
- Read reports\paper_trading\recorded_data_paper_strategy_replay_plan\paper_strategy_replay_plan.json.
- Create no-execution adapter request manifests.
- Enforce broker-disabled and contract-only adapter modes.
- Block strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims.
- Write outputs under reports\paper_trading\recorded_data_paper_strategy_adapter_contract.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_contract.bat.

Expected full quick-check suite after Module DD: 1721 passed.

## Module EE - Recorded data paper strategy adapter contract acceptance gate

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_paper_strategy_adapter_contract\paper_strategy_adapter_contract.json.
- Gate adapter contract status and ready_for_future_adapter flag.
- Enforce configurable minimum adapter requests.
- Enforce configurable minimum total planned bars.
- Verify contract-only adapter mode, no-execution strategy mode, broker-disabled mode, and manifest-only output mode.
- Block execution/trading/profit fields from the adapter contract.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_paper_strategy_adapter_contract_acceptance.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_contract_acceptance.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module EE: 1732 passed.

## Module FF - Recorded data paper strategy adapter readiness gate

Status: implemented in this module.

Scope:
- Run the recorded-data paper strategy adapter contract.
- Run the recorded-data paper strategy adapter contract acceptance gate.
- Write final adapter readiness report under reports\paper_trading\recorded_data_paper_strategy_adapter_readiness.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_readiness.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module FF: 1743 passed.

## Module GG - Recorded data paper strategy adapter dry-run scaffold

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_paper_strategy_adapter_readiness\paper_strategy_adapter_readiness.json.
- Read reports\paper_trading\recorded_data_paper_strategy_adapter_contract\paper_strategy_adapter_requests.jsonl.
- Create deterministic adapter dry-run events.
- Enforce no-execution dry-run mode, broker-disabled mode, and dry-run manifest-only output mode.
- Block strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims.
- Write outputs under reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_dry_run.bat.

Expected full quick-check suite after Module GG: 1754 passed.

## Module HH - Recorded data paper strategy adapter dry-run acceptance gate

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run\paper_strategy_adapter_dry_run.json.
- Gate adapter dry-run status and ready_for_future_adapter_evidence flag.
- Enforce configurable minimum dry-run events.
- Enforce configurable minimum total planned bars.
- Verify dry-run-only mode, no-execution strategy mode, broker-disabled mode, and manifest-only output mode.
- Block execution/trading/profit fields from adapter dry-run output.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_acceptance.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_dry_run_acceptance.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module HH: 1765 passed.

## Module II - Recorded data paper strategy adapter dry-run readiness gate

Status: implemented in this module.

Scope:
- Run the recorded-data paper strategy adapter dry-run scaffold.
- Run the recorded-data paper strategy adapter dry-run acceptance gate.
- Write final adapter dry-run readiness report under reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_readiness.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_dry_run_readiness.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module II: 1776 passed.

## Module JJ - Recorded data paper strategy adapter evidence bundle

Status: implemented in this module.

Scope:
- Run recorded-data paper strategy adapter readiness.
- Run recorded-data paper strategy adapter dry-run readiness.
- Write final adapter evidence bundle under reports\paper_trading\recorded_data_paper_strategy_adapter_evidence_bundle.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_evidence_bundle.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module JJ: 1787 passed.

## Module KK - Recorded data paper strategy adapter evidence bundle acceptance gate

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_paper_strategy_adapter_evidence_bundle\paper_strategy_adapter_evidence_bundle.json.
- Gate bundle status and ready_for_future_adapter_evidence flag.
- Verify required adapter readiness and adapter dry-run readiness stages.
- Verify stage accepted flags and pass/warn status policy.
- Block execution/trading/profit fields from the adapter evidence bundle.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_paper_strategy_adapter_evidence_bundle_acceptance.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_evidence_bundle_acceptance.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module KK: 1798 passed.

## Module LL - Recorded data paper strategy adapter evidence readiness gate

Status: implemented in this module.

Scope:
- Run recorded-data paper strategy adapter evidence bundle.
- Run recorded-data paper strategy adapter evidence bundle acceptance gate.
- Write final adapter evidence readiness report under reports\paper_trading\recorded_data_paper_strategy_adapter_evidence_readiness.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_evidence_readiness.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module LL: 1809 passed.

## v0.4 - Paper Strategy Adapter Evidence Readiness Release

Status: release close implemented.

Release tag:
v0.4-paper-strategy-adapter-evidence-readiness

Closed scope:
- Recorded data paper strategy replay plan scaffold.
- Replay plan acceptance.
- Replay plan readiness.
- Paper strategy adapter contract.
- Adapter contract acceptance.
- Adapter readiness.
- Adapter dry-run scaffold.
- Adapter dry-run acceptance.
- Adapter dry-run readiness.
- Adapter evidence bundle.
- Adapter evidence bundle acceptance.
- Final adapter evidence readiness.

Main command:
.\hqe_recorded_data_paper_strategy_adapter_evidence_readiness.bat

Expected full quick-check suite after v0.4: 1817 passed.

Safety boundary:
This release remains paper/simulation evidence only. It does not execute strategy logic, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, calculate PnL, or prove profitability. This is not a profitability claim.

Next phase:
Future work may add a stricter paper strategy adapter dry-run consumer, but only after this v0.4 evidence readiness layer is tagged and stable.

## Module NN - Recorded data paper strategy adapter dry-run consumer scaffold

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_paper_strategy_adapter_evidence_readiness\paper_strategy_adapter_evidence_readiness.json.
- Read reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run\paper_strategy_adapter_dry_run_events.jsonl.
- Consume dry-run events in audit-only mode.
- Enforce no-strategy-execution consumer mode, broker-disabled mode, and manifest-only output mode.
- Block strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims.
- Write outputs under reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer.bat.

Expected full quick-check suite after Module NN: 1828 passed.

## Module OO - Recorded data paper strategy adapter dry-run consumer acceptance gate

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer\paper_strategy_adapter_dry_run_consumer.json.
- Gate consumer status and ready_for_future_consumer_evidence flag.
- Enforce configurable minimum consumed events.
- Enforce configurable minimum total planned bars.
- Verify audit-only consumer mode, no-execution strategy mode, broker-disabled mode, and manifest-only output mode.
- Block execution/trading/profit fields from adapter dry-run consumer output.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module OO: 1839 passed.

## Module PP - Recorded data paper strategy adapter dry-run consumer readiness gate

Status: implemented in this module.

Scope:
- Run adapter dry-run consumer.
- Run adapter dry-run consumer acceptance gate.
- Write final adapter dry-run consumer readiness report under reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer_readiness.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_readiness.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module PP: 1850 passed.

## Module QQ - Recorded data paper strategy adapter dry-run consumer evidence bundle

Status: implemented in this module.

Scope:
- Run adapter evidence readiness.
- Run adapter dry-run consumer readiness.
- Write final adapter dry-run consumer evidence bundle under reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module QQ: 1861 passed.

## Module RR - Recorded data paper strategy adapter dry-run consumer evidence bundle acceptance gate

Status: implemented in this module.

Scope:
- Read reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle\paper_strategy_adapter_dry_run_consumer_evidence_bundle.json.
- Gate bundle status and ready_for_future_consumer_evidence flag.
- Verify required adapter evidence readiness and consumer readiness stages.
- Verify stage accepted flags and pass/warn status policy.
- Block execution/trading/profit fields from the consumer evidence bundle.
- Write paper/evidence-only output under reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module RR: 1872 passed.

## Module SS - Recorded data paper strategy adapter dry-run consumer evidence readiness gate

Status: implemented in this module.

Scope:
- Run adapter dry-run consumer evidence bundle.
- Run adapter dry-run consumer evidence bundle acceptance.
- Write final consumer evidence readiness report under reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness.
- Add shortcut .\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Expected full quick-check suite after Module SS: 1883 passed.

## v0.5 - Paper Strategy Adapter Consumer Evidence Readiness Release

Status: release close implemented.

Release tag:
v0.5-paper-strategy-adapter-consumer-evidence-readiness

Closed scope:
- Adapter dry-run consumer scaffold.
- Adapter dry-run consumer acceptance.
- Adapter dry-run consumer readiness.
- Adapter dry-run consumer evidence bundle.
- Adapter dry-run consumer evidence bundle acceptance.
- Final adapter dry-run consumer evidence readiness.

Main command:
.\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness.bat

Expected full quick-check suite after v0.5: 1891 passed.

Safety boundary:
This release remains paper/simulation evidence only. It does not execute strategy logic, create signals, create trade plans, connect to brokers, request live market data, place real orders, use real money, calculate PnL, or prove profitability. This is not a profitability claim.

Next phase:
Fast-track v1.0 Testing Edition backtest engine:
- Recorded-data strategy replay sandbox.
- LONG / SHORT / NEUTRAL decision audit.
- CE/PE paper trade-plan simulator.
- Paper fill and exit simulator.
- Backtest ledger and metrics engine.
- One-command paper backtest runner.

## Module UU - Recorded data strategy replay sandbox

Status: implemented in this module.

Scope:
- Read consumer evidence readiness.
- Read recorded-data strategy input bars.
- Validate recorded_replay and paper_simulation_only modes.
- Convert valid bars into strategy replay sandbox events.
- Prepare safe input for future LONG / SHORT / NEUTRAL strategy decision audit.
- Add shortcut .\hqe_recorded_data_strategy_replay_sandbox.bat.
- Keep strategy execution, signal generation, trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Progress:
- Completed total before Module UU: 46 modules.
- v1.0 pending before Module UU: 17 modules.
- v1.0 pending after Module UU: 16 modules.

Expected full quick-check suite after Module UU: 1902 passed.

## Module VV - Recorded data strategy decision audit

Status: implemented in this module.

Scope:
- Read strategy replay sandbox report.
- Validate sandbox event safety/mode fields.
- Convert valid sandbox events into deterministic LONG / SHORT / NEUTRAL decision audit events.
- Preserve decision mapping: LONG = future CE buy paper plan only, SHORT = future PE buy paper plan only, NEUTRAL = no trade.
- Add shortcut .\hqe_recorded_data_strategy_decision_audit.bat.
- Keep CE/PE trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Progress:
- Completed total before Module VV: 47 modules.
- v1.0 pending before Module VV: 16 modules.
- v1.0 pending after Module VV: 15 modules.

Expected full quick-check suite after Module VV: 1913 passed.

## Module WW - Recorded data strategy decision acceptance gate

Status: implemented in this module.

Scope:
- Read strategy decision audit report.
- Validate LONG / SHORT / NEUTRAL decisions.
- Validate LONG = future CE buy paper plan only, SHORT = future PE buy paper plan only, NEUTRAL = no trade.
- Validate decision safety/mode fields.
- Gate decision output before future paper trade-plan simulator.
- Add shortcut .\hqe_recorded_data_strategy_decision_acceptance.bat.
- Keep CE/PE trade plans, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Progress:
- Completed total before Module WW: 48 modules.
- v1.0 pending before Module WW: 15 modules.
- v1.0 pending after Module WW: 14 modules.

Expected full quick-check suite after Module WW: 1924 passed.

## Module XX - Recorded data paper option trade-plan simulator

Status: implemented in this module.

Scope:
- Read strategy decision acceptance gate.
- Read strategy decision audit report.
- Convert LONG decisions into CE BUY paper plans.
- Convert SHORT decisions into PE BUY paper plans.
- Keep NEUTRAL decisions as no trade.
- Add shortcut .\hqe_recorded_data_paper_option_trade_plan_simulator.bat.
- Keep fills, broker/live execution, live market data, real orders, real money, PnL, and profitability claims out of scope.

Progress:
- Completed total before Module XX: 49 modules.
- v1.0 pending before Module XX: 14 modules.
- v1.0 pending after Module XX: 13 modules.

Expected full quick-check suite after Module XX: 1935 passed.

## Module YY - Recorded data paper fill and exit simulator

Status: implemented in this module.

Scope:
- Read paper option trade-plan simulator report.
- Read strategy decision audit report for recorded close references.
- Convert CE/PE paper plans into paper entry/exit lifecycle records.
- Keep broker/live execution, live market data, real orders, real money, account PnL, and profitability claims out of scope.
- Add shortcut .\hqe_recorded_data_paper_fill_exit_simulator.bat.

Progress:
- Completed total before Module YY: 50 modules.
- v1.0 pending before Module YY: 13 modules.
- v1.0 pending after Module YY: 12 modules.

Expected full quick-check suite after Module YY: 1946 passed.

## Module ZZ - Recorded data backtest trade ledger

Status: implemented in this module.

Scope:
- Read paper fill/exit simulator report.
- Validate CE/PE paper lifecycle safety/mode fields.
- Convert valid lifecycle records into paper-only backtest ledger rows.
- Calculate simulated paper reference result using option_points_result * quantity_lots * lot_size.
- Add shortcut .\hqe_recorded_data_backtest_trade_ledger.bat.
- Keep broker/live execution, live market data, real orders, real money, and profitability claims out of scope.

Progress:
- Completed total before Module ZZ: 51 modules.
- v1.0 pending before Module ZZ: 12 modules.
- v1.0 pending after Module ZZ: 11 modules.

Expected full quick-check suite after Module ZZ: 1957 passed.
