# Hunter Quant Engine — Master Roadmap

HQE is not a timepass script. It is a serious market research and execution foundation.

## Current Base State

HQE v0.1 Foundation:

- Clean Python architecture
- 596 tests passing
- FYERS NIFTY 5m historical data download
- SMC detections: BOS, CHOCH, FVG, Order Blocks, Liquidity, Sweeps
- Strategy config system
- Strict/Balanced/Relaxed strategy modes
- Strategy mode CLI support
- Strategy mode benchmark runner
- PC-only strategy mode benchmark shortcut
- Backtest pipeline
- Trades CSV export
- Equity curve export
- Buy-and-hold benchmark comparison
- Token refresh helper
- PC + Laptop GitHub sync
- Private GitHub repository

Current benchmark truth:

- HQE Strategy Return: 0.9883%
- Buy & Hold Return: 2.6990%
- Alpha: -1.7107%
- Result: HQE underperformed buy-and-hold
- Strict/Balanced/Relaxed benchmark runner: built and tested
- Full real-data strategy mode benchmark: pending PC run

This is not a failure. This is the first honest baseline.
Mode comparison must be judged only after costs and only after the PC benchmark run.

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

Outputs:

- experiment_summary.csv
- best_configs.csv
- worst_configs.csv

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

1. Create and commit ROADMAP.md ? DONE
2. Strategy Config System ? DONE
3. Strict/Balanced/Relaxed modes ? DONE
4. Strategy mode benchmark runner ? DONE
5. Full real-data mode benchmark on PC ? PENDING
6. Experiment runner
7. Walk-forward testing
8. Streamlit UI dashboard
9. Broker gateway interfaces
10. Live market observer
11. Paper trading
12. Risk gateway
13. Micro live execution

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
