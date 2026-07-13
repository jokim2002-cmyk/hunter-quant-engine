# HQE Master Product Roadmap

## Purpose

This roadmap prevents HQE from deviating into random modules or unnecessary polish.

Every new task must map to this roadmap.

If a requested task does not support the product vision, it should be rejected, delayed, or parked.

---

## Current completed foundation

The current HQE foundation includes:

- Safe paper-only validation engine
- Data-only broker access base
- Fyers historical 5m data test
- Daily validation reports
- Persistent market-day paper-watch loop
- Dashboard V7 technical validation UI
- Product app MVP with license screen
- Owner license generator MVP
- Customer machine ID flow
- New-PC installer script MVP
- Single desktop shortcut MVP

Current limitation:

- UI is still developer-style
- CMD is still visible for background watch
- Only Fyers data path is meaningful
- Strategy system is not yet generalized
- Backtester is not yet a public app feature
- Real execution is locked and not product-ready

---

## Golden rule

**No more random module work.**

A module is allowed only if it clearly belongs to one of these roadmap phases:

1. Public app simplification
2. Multi-broker data connection
3. Strategy builder / strategy packs
4. Backtesting engine
5. Paper validation
6. Reporting
7. Installer/licensing
8. Future risk-gated real execution

---

## Phase 1 — Public Trader App V2

Goal: Remove CMD/PowerShell from normal user experience.

Build:

- Modern attractive HQE home screen
- Better decorative HQE app icon
- One-click start flow
- Hidden background paper-watch runner
- App-based live status cards
- App-based internet status
- App-based broker status
- App-based data status
- App-based today report viewer
- App-based evidence viewer
- Simple language UI

User should see:

- Internet: OK / Disconnected
- Broker: Connected / Login expired
- Market data: Live / Waiting
- Strategy: Ready / Not selected
- Paper trading: Running / Stopped
- Today: Waiting for setup / Trade found / No trade / Report ready

Exit criteria:

- User can use HQE from one app window.
- CMD/PowerShell is not required in daily use.
- App shows clear status even when internet or broker fails.
- App remains paper-only and safe.

---

## Phase 2 — Broker Connect Center

Goal: Support multiple popular brokers in app.

Broker list:

- Fyers
- Zerodha
- Angel One
- Upstox
- Groww
- Dhan

Build:

- Broker selection screen
- Broker-specific API credential form
- Secret storage in local encrypted/config folder
- Auth URL helper
- Token refresh inside app
- Connection test button
- Broker status dashboard
- Internet status monitor
- Token-expiry warning
- Last-data-time display
- Broker adapter interface

Initial safety:

- Data-only for all brokers
- No order APIs enabled
- No real execution

Exit criteria:

- User can connect broker API from app without PowerShell.
- App can show whether broker/data connection is working.
- Broker credentials are not pasted into chat.
- HQE can add new brokers through adapters.

---

## Phase 3 — Market Data Layer

Goal: Create unified market data system independent of one broker.

Build:

- Historical candle fetch interface
- Live market data interface
- Data normalization
- Symbol mapping
- Stocks data
- Index data
- Options chain data
- Futures data
- Data quality checks
- Missing candle detection
- Internet/data outage handling
- Cached fallback view

Exit criteria:

- HQE can feed backtests and paper validation from normalized data.
- Broker-specific data is converted into one HQE format.
- User sees simple data status, not technical files.

---

## Phase 4 — Strategy Builder / Strategy Pack System

Goal: Let HQE handle different trader strategies.

Build:

- Strategy category selection:
  - Stocks intraday
  - Stocks swing
  - Holdings
  - Options buying
  - Options selling simulation
  - Futures
  - Custom CSV signal
- Entry rule builder
- Exit rule builder
- Risk rule builder
- Time filter
- Indicator library
- Price-action rule library
- Strategy import/export
- Strategy Pack format
- Strategy Pack validation
- Strategy Pack versioning

Customer model:

- Customer explains strategy.
- Owner converts it into HQE Strategy Pack.
- App can import and run it.

Exit criteria:

- HQE is no longer locked to one NIFTY option-buy setup.
- A strategy can be selected, tested, and reported from the app.

---

## Phase 5 — Backtesting Engine Productization

Goal: Make HQE’s core value visible to traders.

Build:

- Backtest screen
- Date range selector
- Instrument selector
- Capital/risk settings
- Charges/slippage settings
- Run backtest button
- Simple backtest report
- Equity curve
- Drawdown chart
- Trade list
- Day-wise result
- Market-condition breakdown
- Strategy pass/fail decision

Backtest report should answer:

- Did this strategy work historically?
- How risky was it?
- How many trades?
- What was the worst phase?
- Is it ready for paper validation?

Exit criteria:

- Non-coder trader can run and understand a backtest.
- App does not show raw technical files by default.
- Detailed evidence remains available for audit.

---

## Phase 6 — Paper Validation Productization

Goal: Turn current validation engine into app-based workflow.

Build:

- Start Paper Validation button
- Stop/Pause button
- Validation progress card
- Observed days
- Valid trade-days
- Total paper trades
- No-trade reasons
- Daily report
- Weekly report
- Expiry week tracker for options
- Strategy drift warning
- Data outage warning
- Kill switch display
- Report export

Exit criteria:

- User can run paper validation without terminal.
- App explains no-trade days clearly.
- No fake trades are created.
- Strategy cannot be secretly tuned during validation.

---

## Phase 7 — Reports and Evidence System

Goal: Make reports beautiful and understandable.

Build:

- Today Report
- Backtest Report
- Paper Validation Report
- Strategy Report
- Risk Report
- Broker/Data Health Report
- Export PDF/HTML
- Export ZIP
- Customer-friendly summary
- Owner audit view

Report language:

- Simple summary first
- Detailed evidence second
- Warnings clearly visible
- No profitability guarantee

Exit criteria:

- Customer can understand result without reading logs.
- Owner can audit deeper evidence if needed.

---

## Phase 8 — Installer, Licensing, and Product Delivery

Goal: Make HQE installable and sellable.

Build:

- Proper Windows installer
- One desktop icon
- Decorative app icon
- License activation
- Owner license generator
- Customer machine ID flow
- License expiry
- Customer user guide
- Owner seller guide
- App update process
- Backup/restore config
- Uninstall process

Future licensing:

- Offline license MVP now
- Online license server later
- Device binding
- Expiry/renewal
- Feature-level access

Exit criteria:

- Customer can install with simple instructions.
- Owner can issue user keys.
- Master/private key never leaves owner system.

---

## Phase 9 — Real Execution Gateway

Goal: Only after all prior phases, consider controlled real-money execution.

This phase is locked until:

- Multi-broker data layer works
- Strategy builder works
- Backtesting works
- Paper validation works
- Risk gateway works
- Reports work
- App UI is simple
- Compliance review is done

Build later:

- Broker order adapters
- Order preview screen
- Manual confirm mode
- Real trading unlock key
- Daily max loss
- Max order quantity
- Strategy-level risk cap
- Kill switch
- Auto square-off
- Audit log
- Real/Paper mode separation
- Emergency stop

Default:

**Real Trading Locked**

Exit criteria:

- No accidental real order possible.
- User clearly understands real-money risk.
- Every order is logged.
- Kill switch is always available.

---

## Phase 10 — Scale and Marketplace

Goal: Long-term HQE platform.

Future possibilities:

- Strategy marketplace
- Customer strategy packs
- Broker plugin marketplace
- Cloud sync
- Owner dashboard
- License server
- Team/customer management
- Analytics dashboard
- Education mode
- Strategy templates

This phase is not current priority.

---

## Immediate next build

Next build should be:

**HQE App V2 Public Trader UI + Multi-Broker Architecture Pack**

Scope:

- Modern attractive app UI
- Hidden background runner
- No visible CMD in daily use
- Broker connect screen with 6 broker placeholders
- Internet status card
- Broker status card
- Market data status card
- Paper watch status card
- Today report inside app
- Simple trader language
- Safety locks preserved

Do not build real orders yet.

---

## Work priority order

1. App V2 no-CMD public UI
2. Multi-broker connect architecture
3. Market data abstraction
4. Strategy Pack system
5. Backtest UI
6. Paper validation UI
7. Reports UI
8. Installer/licensing improvement
9. Real execution gateway only after review

---

## Decision rule for future chats

Before doing any work, ask:

1. Does this task move HQE toward a simple usable product?
2. Does it reduce trader complexity?
3. Does it improve broker/strategy/backtest/paper/report flow?
4. Does it preserve safety?
5. Is it required before real money?

If answer is no, do not do it.

---

## Definition of success

HQE is successful when a non-coder retail trader can:

1. Install HQE.
2. Open one app icon.
3. Connect broker.
4. Create/import strategy.
5. Run backtest.
6. Run paper validation.
7. Understand report.
8. Decide safely whether strategy deserves more testing.

No coding. No CMD. No confusion.

## Stabilization Bunch 1 - App usability repair

Status: COMPLETED AFTER TEST PASS.

This repair closes the immediate desktop usability blockers: missing main
scrolling, hidden Advanced Tools access, slow visible startup, stale shortcut
routing, and unsafe Git visibility of local machine-bound license files.

Next roadmap bunch: test and repair every app-center action end to end, then
continue product completion from the master roadmap without reopening real
execution scope.

## Current Stabilization Priority — Bunch 2

- Callback crash recovery
- Button callback integrity
- Persistent local UI error logging
- Paper-only safety regression

Next: full operator button smoke and remaining slow-center optimization.

## Current Stabilization Priority — Bunch 3

- Repair app-center dialog palette compatibility
- Restore missing feature callback
- Real GUI smoke for all safe app centers
- Safety regression

Next: final startup/performance polish and operator UI defect repair.

## Current Stabilization Priority â€” Bunch 4

Status: COMPLETED AFTER TEST PASS.

- Refresh stale paper-only RC hashes after approved stabilization changes
- Verify release-candidate and operator-acceptance integrity
- Preserve all execution locks

Next: startup performance profiling, lazy-loading verification, and operator UI polish.
