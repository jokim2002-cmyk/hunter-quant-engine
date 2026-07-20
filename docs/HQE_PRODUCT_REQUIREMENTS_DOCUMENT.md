# Hunter Quant Engine (HQE)
# Product Requirements Document

**Document ID:** HQE-PRD-001
**Version:** 1.0
**Status:** Product baseline and future-live roadmap
**Date:** 2026-07-20
**Product:** Hunter Quant Engine
**Primary owner:** HQE Owner / Operator
**Target platform:** Windows desktop
**Current production scope:** Paper trading, data, research, backtesting, strategy management and evidence
**Future approved scope:** Controlled real-money execution through a separately gated execution gateway

---

## 1. Document purpose

This document is the formal Product Requirements Document for Hunter Quant
Engine (HQE).

It consolidates the existing HQE product vision, master roadmap, paper-only
release, multi-strategy architecture, licensing, broker/data design, backtesting,
forward paper validation, reports, release controls and the future path to
real-money trading.

This PRD is the top-level product contract. Future coding, UI changes, broker
integrations, strategy work, paper validation and live-execution work must map
to a requirement in this document.

---

## 2. One-line product vision

**HQE will be a simple, trader-friendly strategy research, backtesting,
paper-validation and controlled-execution platform that allows a retail trader
to test, understand and later run approved strategies without needing coding
knowledge.**

Product principle:

> **Simple for the trader. Strict for the engine. Safe by default.**

---

## 3. Product problem

Retail traders commonly face these problems:

- Strategy logic is scattered across scripts or broker tools.
- Backtest and live logic may not be identical.
- Results may ignore charges, slippage, liquidity or data quality.
- Paper reports may show signals without maintaining a real paper position.
- Technical reports are difficult for a non-coder to understand.
- Broker credentials, execution and risk controls are often mixed together.
- Strategy changes during validation can invalidate evidence.
- Real-money trading may be enabled without sufficient controls.
- A trader may not be able to prove why an order was or was not taken.

HQE must solve these problems through one controlled product flow:

1. Connect or import data.
2. Select or create a strategy.
3. Validate the strategy package.
4. Backtest it.
5. Run forward paper validation.
6. Review evidence and risk.
7. Approve or reject the strategy.
8. Only in a future gated release, permit controlled real-money execution.

---

## 4. Target users

### 4.1 Retail trader

A non-coder who wants to test and operate a strategy through a clear desktop
application.

### 4.2 HQE owner/operator

The person responsible for licensing, strategy approval, release approval,
risk configuration, live-mode authorization and emergency control.

### 4.3 Strategy developer or reviewer

A person who creates, imports, reviews, validates and versions strategy packs.

### 4.4 Support or audit operator

A person who reviews logs, reports, state, broker health, order evidence and
release evidence without changing strategy logic.

---

## 5. Current verified product boundary

The current HQE release is a protected **paper/data/research-only** product.

Current capabilities include:

- Windows desktop application
- Product license verification
- Stable machine identity
- Fyers data-only connection path
- Market-data and internet status
- CE BUY and PE BUY paper lifecycle
- OPEN, HELD and CLOSED paper-position states
- Entry, stop loss, target and latest option price
- Unrealized and realized paper P&L
- Paper ledger and history
- Restart recovery
- Start and Stop controls
- Duplicate-start protection
- Background runtime without a visible CMD window
- Today Report and technical evidence
- Strategy registry and strategy-pack metadata
- Product Strategy Manager
- Reviewed import workflow
- One-active paper configuration
- Parallel isolated observation for research
- Release, freeze and validation evidence

Current release mode:

```text
PAPER ONLY
DATA ONLY
RESEARCH ONLY
NO REAL ORDERS
NO BROKER EXECUTION
NO AUTO TRADING
NO REAL MONEY
NO OPTION SELLING
```

The existing paper-only baseline must remain recoverable and usable while
future live-readiness work is developed separately.

---

## 6. Product goals

### G-001: Trader-friendly operation

A normal daily user must be able to install, activate, open and operate HQE
without PowerShell, CMD, JSON editing or source-code knowledge.

### G-002: One strategy implementation

The same reviewed strategy implementation and parameters must be used across:

- historical backtest
- recorded-data replay
- forward paper validation
- future shadow execution
- future real execution

### G-003: Evidence before execution

HQE must produce inspectable evidence for every important decision:

- signal accepted or rejected
- trade opened or not opened
- order allowed or blocked
- position held or closed
- risk control invoked
- operator action
- broker acknowledgement
- reconciliation result

### G-004: Safe multi-strategy platform

A new strategy must be addable through a versioned contract and registry without
rewriting the HQE core.

### G-005: Controlled future real money

Real-money trading may be introduced only through a separately developed,
separately reviewed, disabled-by-default execution gateway after all mandatory
gates pass.

### G-006: No profitability promise

HQE must never claim guaranteed profit or guaranteed income. Product quality is
measured by correctness, safety, evidence, reliability and usability.

---

## 7. Non-goals in the current release

The following are not enabled in the current release:

- real broker order placement
- automatic live execution
- real-money positions
- option selling
- uncontrolled multi-strategy live trading
- automatic selection of a â€œbestâ€ strategy
- live scaling based only on backtest profit
- guaranteed-profit claims
- hidden broker actions
- customer access to owner private licensing keys

---

## 8. Product principles and permanent invariants

### PR-001: Fail closed

When data, license, broker, strategy, risk, clock, reconciliation or state is
uncertain, HQE must block the action rather than guess.

### PR-002: Explicit mode separation

The UI and reports must clearly distinguish:

- historical backtest
- recorded replay
- paper trading
- shadow live observation
- broker sandbox
- real-money execution

A user must never confuse a signal evaluation with an executed paper trade or a
real broker order.

### PR-003: No hidden execution

No real broker call may occur unless the product is in an explicitly unlocked
live mode and every required gate has passed.

### PR-004: Strategy immutability during validation

A strategy under validation must be version-locked. Any logic or parameter
change starts a new validation identity and new evidence period.

### PR-005: Full traceability

Every trade, order intent, broker response, position change and operator action
must be traceable to:

- strategy ID and version
- parameter hash
- data timestamp and source
- risk decision
- order or paper-position identity
- application release
- machine and workspace identity
- operator action where applicable

### PR-006: No fake trades

A report must not describe an executed paper trade unless HQE created a paper
position and maintained its lifecycle.

A strategy signal or accepted evaluation must be labelled as a signal or
evaluation, not as a trade.

### PR-007: Protected baseline

The current paper-only release must not be casually rewritten while live
execution is being designed. Live work must use isolated branches, modules and
release gates.

---

## 9. Product experience requirements

### UX-001: One desktop icon

HQE must launch from one branded Windows desktop icon.

### UX-002: No developer console in normal use

Normal installation, launch, paper operation, reporting and future live
operation must not require a visible CMD or PowerShell window.

### UX-003: Clear status

The main application must show clear trader-language status for:

- internet
- license
- selected broker
- broker authentication
- market data
- selected strategy
- paper watch
- live mode
- risk lock
- kill switch
- report readiness

### UX-004: Mode banner

The application must show the current operating mode prominently.

Examples:

```text
PAPER ONLY - NO REAL ORDERS
SHADOW LIVE - ORDERS BLOCKED
LIVE MANUAL CONFIRMATION - REAL MONEY
LIVE AUTOMATION - REAL MONEY
```

### UX-005: Trader-language errors

Errors must explain what failed, whether money or orders were affected, what
remains safe and the next safe action.

### UX-006: Today Report

The daily report must distinguish evaluations, accepted signals, paper trades,
real orders, positions, P&L, blocked actions, safety events and data or broker
gaps.

---

## 10. Licensing and identity requirements

### LIC-001

HQE must support machine-bound product license verification.

### LIC-002

The product must use a stable machine identity and must not generate a different
identity during normal restarts.

### LIC-003

The owner private key must never be included in customer releases, reports,
repositories intended for distribution or public support packages.

### LIC-004

License state and broker authorization must remain separate. A valid HQE license
must not automatically authorize broker execution.

### LIC-005

License failure must block the product safely without modifying strategy,
position, ledger or broker state.

### LIC-006

License recovery must preserve existing valid keys where possible and must not
generate a new owner identity without explicit owner action.

---

## 11. Broker and market-data requirements

### DATA-001: Multi-broker architecture

HQE must use a broker-neutral interface. Planned broker families include Fyers,
Zerodha, Angel One, Upstox, Groww and Dhan.

A broker is considered supported only after its adapter, tests, operational
guide and release evidence pass.

### DATA-002: Separate data and execution permissions

Each broker adapter must expose separate capabilities:

- authentication
- historical data
- live market data
- account data
- order simulation or sandbox
- real order execution

Data permission must not imply execution permission.

### DATA-003: Data freshness

Paper and future live decisions must be blocked when required market data is
stale, incomplete, out of sequence or outside the approved trading session.

### DATA-004: Time integrity

HQE must use a defined exchange/session timezone and record timestamps in a
consistent, auditable format.

### DATA-005: Contract and instrument validation

Before evaluation or order creation, HQE must validate exchange, instrument,
symbol, expiry, strike, option type, lot size, tick size, trading session and
supported product type.

### DATA-006: Broker health

The UI must expose token health, connection health, rate-limit state and last
successful broker communication.

### DATA-007: Secrets

Broker secrets and access tokens must not be printed in logs, reports,
screenshots or support bundles. Secure storage and token refresh must be
implemented before real execution.

---

## 12. Strategy system requirements

### STR-001: Versioned strategy contract

Every strategy must have a versioned manifest containing at least:

- unique strategy ID
- strategy name
- version
- supported instruments
- supported modes
- input requirements
- parameters and types
- entry logic identity
- exit logic identity
- risk defaults
- required filters
- validation requirements
- compatibility version
- package hash
- approval status

### STR-002: Deterministic output

The canonical strategy output must be:

```text
LONG
SHORT
NEUTRAL
```

Default option-buy mapping:

```text
LONG    -> CE_BUY
SHORT   -> PE_BUY
NEUTRAL -> NO_TRADE
```

Any different mapping must be declared explicitly in the strategy manifest.

### STR-003: Validation meaning

`VALID` in Product Strategy Manager means the package structure and declared
requirements are valid.

It does **not** mean profitable, live-ready, fully implemented, reviewed for the
current runtime or approved for real money.

### STR-004: Strategy lifecycle states

A strategy may move through:

```text
DRAFT
SCHEMA_VALID
IMPLEMENTATION_CONNECTED
BACKTEST_REVIEWED
PAPER_VALIDATING
PAPER_VALIDATED
SHADOW_APPROVED
LIVE_CANDIDATE
LIVE_APPROVED
SUSPENDED
RETIRED
```

No state may be skipped without an approved evidence record.

### STR-005: Same logic across modes

Backtest, paper and future live execution must call the same strategy decision
implementation. Mode-specific code may handle data, positions and orders, but
must not silently change entry or exit logic.

### STR-006: Safe imports

Imported strategy packs must be reviewed, schema-validated, hash-recorded and
installed atomically. Invalid packages must not damage the working registry.

### STR-007: One active canonical strategy first

Canonical paper and future live trading must initially allow one active strategy
identity at a time.

A strategy switch must be blocked while a paper or real position is open, an
order is pending, reconciliation is incomplete or the session is locked.

### STR-008: Parallel observation

Multiple strategies may run simultaneously only in isolated observation lanes
unless a future multi-strategy execution release is separately approved.

Each lane must have separate state, ledger, P&L, reports, evidence and restart
recovery. Parallel observation must not automatically change the canonical
active strategy.

### STR-009: Current seven strategy packs

The current seven packs are product templates and research candidates. Their
presence in the registry does not make them live-ready.

Before any pack is eligible for real money, it must have:

- an executable reviewed implementation
- parameter validation
- backtest evidence
- forward paper evidence
- locked version and hash
- risk profile
- operator approval
- live-readiness approval

---

## 13. Backtesting requirements

### BT-001

The application must allow a trader to choose strategy, strategy version,
parameters, instrument, date range, timeframe, cost model, slippage model and
capital model.

### BT-002

Backtest outputs must include at least:

- number of evaluations
- number of signals
- number of trades
- gross and net result
- configured charges and slippage
- maximum drawdown
- win rate
- average gain and loss
- risk/reward distribution
- consecutive wins and losses
- exposure time
- market-regime breakdown
- rejected or skipped reasons
- data-quality warnings

### BT-003

Backtest results must record the strategy package hash, parameter hash, data
identity and HQE release identity.

### BT-004

HQE must support train, validation and out-of-sample periods where appropriate.

### BT-005

Backtest results must not be presented as proof of future profitability.

### BT-006

A strategy must not enter paper validation when the backtest is invalid,
non-reproducible, materially data-defective or missing the approved cost model.

---

## 14. Paper-validation requirements

### PAPER-001: Actual paper lifecycle

A paper trade exists only after HQE creates a paper position with:

- position ID
- strategy identity
- entry timestamp
- entry price
- quantity
- stop loss
- target
- latest price
- position status
- exit timestamp and price when closed
- realized or unrealized P&L
- reason logs

### PAPER-002: Signal versus trade

Reports must separately count evaluations, LONG/SHORT/NEUTRAL decisions,
accepted signals, rejected signals, opened paper trades and closed paper trades.

### PAPER-003: Validation plan

Each strategy must have an approved validation plan defining minimum observed
market days, paper trades, market regimes, expiry-week coverage for options,
data-health coverage, acceptable incidents, drawdown limits and recovery tests.

The existing candidate floor may be used as a starting floor, but live approval
may require stricter evidence.

### PAPER-004: No tuning during validation

A logic or parameter change invalidates the current validation identity and
starts a new validation cycle.

### PAPER-005: Costs and liquidity

Paper P&L must use an approved model for charges, spread, slippage and fill
assumptions. Unrealistic fills must be flagged.

### PAPER-006: Recovery

Paper state, ledger and reports must recover after a normal restart without
creating duplicate positions or duplicate entries.

### PAPER-007: Daily close

The user must be able to stop the session, generate a daily report and inspect
technical evidence.

---

## 15. Reports and evidence requirements

### REP-001

Every run must produce human-readable and machine-readable evidence.

### REP-002

Human-readable reports must use trader language.

### REP-003

Technical evidence must contain enough information to reproduce or audit the
decision.

### REP-004

Reports must clearly state the operating mode and whether a signal was generated,
a paper trade was opened, a real order was created, a broker accepted the order,
a position exists and P&L is simulated or real.

### REP-005

Evidence must be immutable for a frozen release except through a versioned,
audited migration.

### REP-006

A release must include freeze, validation, smoke and acceptance evidence.

---

## 16. Future real-money execution gateway

This section defines the future target. It does not activate real trading in the
current product.

### 16.1 Architecture boundary

Real execution must be implemented as a separate, narrow execution gateway.
The strategy engine may produce an approved order intent. Only the execution
gateway may translate that intent into a broker order.

The gateway must never accept an unvalidated raw strategy signal directly.

Canonical flow:

```text
Market data
  -> Strategy decision
  -> Position/order intent
  -> Pre-trade risk engine
  -> Human confirmation or approved automation gate
  -> Execution gateway
  -> Broker acknowledgement
  -> Order and position reconciliation
  -> Audit evidence
```

### LIVE-001: Default locked

All new installations, upgrades, workspaces and strategies must default to:

```text
REAL TRADING LOCKED
```

### LIVE-002: Separate approval

Live mode must require a dedicated live-release build and explicit owner/admin
approval. A paper release must never become live merely through a UI toggle.

### LIVE-003: Live-capable strategy

Only a strategy in `LIVE_APPROVED` state may create a real order intent.

### LIVE-004: Immutable live identity

The live strategy ID, version, package hash and parameter hash must be locked
for the session.

### LIVE-005: Pre-trade risk engine

Every order intent must be checked against configurable hard limits including:

- allowed broker account
- allowed exchange and instrument
- allowed product type
- allowed side
- allowed trading session
- maximum quantity
- maximum order value
- maximum position value
- maximum number of open positions
- maximum trades per day
- maximum daily realized loss
- maximum daily total loss
- maximum strategy drawdown
- maximum spread
- maximum slippage or price deviation
- minimum data freshness
- cooldown
- duplicate-order protection
- available funds or margin
- circuit and exchange restrictions where available

A missing or unreadable limit must block the order.

### LIVE-006: Initial manual confirmation

The first live release must require a deliberate per-order human confirmation
after showing instrument, side, quantity, estimated price, estimated order
value, strategy and reason, stop and target, current daily P&L and remaining risk
budget.

Automatic execution must remain disabled in this stage.

### LIVE-007: Gradual capital progression

Live rollout must progress through controlled stages:

1. shadow live observation with no orders
2. broker sandbox or simulation where available
3. live manual-confirmation mode with minimal approved capital
4. supervised limited automation
5. broader automation only after new approval

Passing one stage does not automatically unlock the next.

### LIVE-008: Kill switches

HQE must provide:

- global emergency stop
- broker-specific stop
- strategy-specific stop
- new-order stop
- flatten-position workflow where supported and explicitly confirmed
- automatic stop on daily-loss breach
- automatic stop on stale data
- automatic stop on broker desynchronization
- automatic stop on repeated order rejection
- automatic stop on internal exception affecting order safety

The emergency stop must be visible and testable.

### LIVE-009: Idempotency and duplicate prevention

Every order intent must have a unique idempotency identity. Restart, retry,
double-click or network timeout must not create a duplicate order.

### LIVE-010: Broker acknowledgement

HQE must not mark a real order as accepted until broker acknowledgement is
received and validated.

### LIVE-011: Reconciliation

HQE must regularly reconcile intended orders, submitted orders, broker orders,
fills, open positions, local ledger and available funds or margin where permitted.

Any mismatch must pause new orders and raise an operator alert.

### LIVE-012: Partial fills and rejections

The execution state machine must explicitly handle:

```text
PENDING
OPEN
PARTIALLY_FILLED
FILLED
CANCELLED
REJECTED
EXPIRED
UNKNOWN
RECONCILIATION_REQUIRED
```

### LIVE-013: Restart recovery

After a restart, HQE must first read broker truth and reconcile before permitting
a new order.

### LIVE-014: Secure credentials

Real-execution credentials must use secure local storage and least privilege.
Secrets must never be stored in strategy packs or plain-text reports.

### LIVE-015: Operator consent

Live unlock must record operator identity, timestamp, broker account, strategy
identity, risk profile, approved capital limit, release identity and consent.

### LIVE-016: Distinct visual mode

Real-money mode must use an unmistakable visual state and repeated confirmation.
It must not look identical to paper mode.

### LIVE-017: Audit log

Every real-money decision and broker interaction must be written to an
append-only audit log with timestamps and correlation IDs.

### LIVE-018: Fail-safe network behavior

A network failure must not cause repeated blind order submission. Unknown order
state must enter reconciliation-required mode.

### LIVE-019: No option selling by default

Option selling remains excluded until a separate PRD amendment, risk model,
margin model, stress testing, broker controls and explicit approval are complete.

### LIVE-020: Legal, regulatory and broker review

Before live release, HQE must complete documented review against applicable law,
regulatory requirements, exchange rules and broker terms for the intended user,
account, instruments and operating mode.

This PRD does not itself certify regulatory approval.

---

## 17. Real-money release gates

No live release is permitted until every required gate is PASS.

### Gate L0: Protected paper baseline

- paper release recoverable
- paper reports correct
- license and shortcut stable
- no real execution path in the paper build

### Gate L1: Strategy readiness

- executable reviewed implementation
- deterministic backtest/paper parity
- version and parameter lock
- approved backtest evidence
- approved paper-validation evidence
- risk profile approved
- no unresolved critical strategy defects

### Gate L2: Data readiness

- live data adapter tested
- freshness checks tested
- session and instrument validation tested
- disconnect behavior tested
- replay and live consistency reviewed

### Gate L3: Execution gateway readiness

- gateway isolated from strategy code
- broker adapter contract tested
- all real calls blocked by default
- idempotency tested
- rejection and partial-fill handling tested
- reconciliation tested

### Gate L4: Risk readiness

- all hard limits configured
- missing limits block execution
- daily-loss lock tested
- quantity and value limits tested
- stale-data lock tested
- kill switches tested
- restart recovery tested

### Gate L5: Security readiness

- secrets protected
- logs scrubbed
- license and broker identity separated
- private owner keys excluded
- dependency and release integrity verified

### Gate L6: Operational readiness

- operator guide complete
- incident runbook complete
- emergency-stop drill passed
- broker outage drill passed
- duplicate-order drill passed
- manual visual acceptance passed

### Gate L7: Compliance and consent

- applicable review complete
- broker-account compatibility confirmed
- owner/admin approval recorded
- user consent recorded
- approved capital and instruments recorded

### Gate L8: Micro-live approval

- dedicated live release
- minimal approved capital
- per-order confirmation
- close monitoring
- daily post-trade reconciliation
- explicit stop conditions

### Gate L9: Automation approval

Automatic real trading requires a new approval after successful supervised
micro-live evidence. It is not included automatically in micro-live approval.

---

## 18. Non-functional requirements

### NFR-001: Reliability

The product must recover safely from normal restart, internet interruption and
broker reconnect without duplicate positions or orders.

### NFR-002: Determinism

Given the same approved data, strategy version and parameters, the strategy
decision layer must produce the same output.

### NFR-003: Auditability

Critical decisions must be explainable and traceable.

### NFR-004: Security

Secrets, owner keys and customer data must be protected according to their risk.

### NFR-005: Performance

UI actions must remain responsive. Strategy evaluation and risk checks must
complete within the defined operating budget for the selected timeframe.

### NFR-006: Compatibility

Supported Windows versions, runtime packaging and broker dependencies must be
declared in each release.

### NFR-007: Maintainability

New strategies and brokers must be added through contracts and adapters rather
than scattered conditional logic.

### NFR-008: Testability

Every safety lock, execution gate, strategy state and order state must be
testable without real money.

### NFR-009: Observability

HQE must expose health, last successful action, current mode and blocking reason.

### NFR-010: Accessibility of evidence

A trader must be able to understand the normal report, while a technical
reviewer can inspect deeper evidence.

---

## 19. Testing requirements

Every implementation phase must include the relevant subset of:

- unit tests
- schema tests
- contract tests
- deterministic replay tests
- backtest/paper parity tests
- broker-adapter tests
- risk-engine tests
- state-machine tests
- restart-recovery tests
- duplicate-order tests
- stale-data tests
- disconnection tests
- partial-fill tests
- reconciliation tests
- license tests
- security tests
- UI callback tests
- visual smoke tests
- full regression
- release preflight
- freeze-manifest verification

Real-order tests must use mocks, sandbox or disabled adapters until micro-live is
explicitly approved.

---

## 20. Release and change-control requirements

### REL-001

Development must occur in complete roadmap phases or cohesive implementation
batches with backups, tests and one combined validation report.

### REL-002

A phase checkpoint may be committed and pushed only after its required gates
pass.

### REL-003

Protected master must remain unchanged until explicit merge approval.

### REL-004

A release must identify product version, commit, release mode, enabled and
disabled capabilities, strategy compatibility, broker compatibility, tests,
freeze evidence and known limitations.

### REL-005

A paper-only release must not contain an accidentally reachable live-order path.

### REL-006

A live release must be a separate version with explicit live-mode labelling and
a rollback plan.

---

## 21. Product roadmap

### Phase A: Formal product baseline

- adopt this PRD
- preserve current paper-only release
- update source-of-truth documentation
- define requirement traceability

### Phase B: Strategy truth and productization

- classify all current strategy packs
- distinguish metadata templates from executable implementations
- connect approved strategies to the common runtime
- prove backtest and paper parity

### Phase C: Backtesting product

- trader-facing backtest center
- charges and slippage
- comparison and evidence
- out-of-sample workflow

### Phase D: Paper-validation product

- actual per-strategy paper positions
- validation progress
- stability and recovery
- operator acceptance

### Phase E: Live-data shadow mode

- live broker data
- real account truth where permitted
- no real orders
- shadow order-intent and reconciliation evidence

### Phase F: Disabled execution gateway

- broker order contract
- hard execution firewall
- risk engine
- mocks and sandbox
- real calls disabled

### Phase G: Supervised micro-live

- dedicated live release
- one broker
- one approved strategy
- one approved account
- one approved instrument scope
- minimal approved capital
- per-order human confirmation
- strict kill switches

### Phase H: Limited automation

- separately approved
- supervised rollout
- narrow limits
- continuous reconciliation
- automatic shutdown on anomalies

### Phase I: Scale

- additional brokers
- additional approved strategies
- controlled multi-strategy execution
- marketplace or customer strategy packs
- enterprise monitoring

---

## 22. Success metrics

Product success must be measured through:

- zero unauthorized real orders
- zero duplicate real orders
- 100% real-order traceability
- 100% mode labelling in reports
- successful restart reconciliation
- successful kill-switch tests
- reproducible strategy decisions
- complete paper-trade lifecycle evidence
- reduction in operator confusion
- stable desktop launch and license behavior
- full release-gate pass rate

Strategy profit is not a guaranteed product metric.

---

## 23. Definition of done for the complete HQE vision

HQE reaches the complete product vision when a non-coder retail trader can:

1. Install HQE.
2. Open one desktop application.
3. Activate a valid license.
4. Connect a supported broker.
5. Create or import a strategy.
6. Validate its package.
7. Run a reproducible backtest.
8. Run genuine paper validation.
9. Understand the daily and final reports.
10. See exact strategy, risk and data status.
11. Submit a real order only through an explicitly approved live gateway.
12. Stop execution immediately through a tested kill switch.
13. Reconcile HQE state with broker truth.
14. Audit every decision and order.
15. Use the product without coding or normal CMD/PowerShell operation.

---

## 24. Decisions still requiring explicit approval

The following decisions are intentionally not assumed by this PRD:

- first live broker
- first live strategy
- first live instrument scope
- approved starting capital
- per-trade and daily-loss limits
- manual confirmation duration
- conditions for limited automation
- legal/compliance sign-off process
- customer versus owner-only live usage
- option-selling scope
- cloud versus local deployment
- data-retention policy

Until these are approved, real-money trading remains locked.

---

## 25. Requirement priority

### P0: Mandatory safety and correctness

- mode separation
- no hidden real orders
- strategy identity
- risk engine
- kill switch
- idempotency
- reconciliation
- licensing and secrets
- audit trail
- fail-closed behavior

### P1: Core product

- broker/data connection
- strategy management
- backtesting
- paper validation
- reports
- installer and desktop app

### P2: Advanced product

- parallel research
- strategy comparison
- multiple brokers
- limited automation
- marketplace

P2 work must not delay or weaken P0 controls.

---

## 26. Source-of-truth references

This PRD is based on the existing HQE source-of-truth set, including:

- `README.md`
- `docs/HQE_MASTER_PRODUCT_VISION.md`
- `docs/HQE_MASTER_PRODUCT_ROADMAP.md`
- `docs/HQE_CONSTRUCTION_FLOW_AND_CHAT_HANDOVER.md`
- `docs/HQE_CURRENT_STATUS.md`
- `docs/HQE_MULTI_STRATEGY_ROADMAP.md`
- `docs/HQE_MASTER_HANDOVER_PROMPT.md`
- `docs/HQE_FINAL_PAPER_ONLY_RC_SIGNOFF.md`
- `docs/HQE_PAPER_ONLY_RC_OPERATOR_GUIDE.md`
- `release/HQE_PAPER_ONLY_RC_FREEZE_MANIFEST.json`
- `release/HQE_MULTI_STRATEGY_PHASE8_RELEASE_CLOSURE.json`
- `release/HQE_WINDOWS_RELEASE_MANIFEST.json`

When these documents conflict, this PRD controls product intent, while the
latest verified release evidence controls what is currently implemented.

---

## 27. Final product rule

> **No strategy reaches real money because it exists, validates structurally or
> looks profitable in a backtest. It reaches real money only after executable
> parity, paper evidence, risk controls, operational readiness, compliance
> review and explicit human approval all pass.**

Current status:

```text
HQE PAPER/DATA/RESEARCH PRODUCT: AVAILABLE
HQE REAL-MONEY EXECUTION: FUTURE, GATED AND LOCKED
```
