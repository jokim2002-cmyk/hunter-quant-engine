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

## Current Stabilization Priority — Bunch 5

Status: COMPLETED AFTER TEST PASS.

- Remove blocking status work from first-window startup
- Keep network and process discovery off the Tkinter UI thread
- Preserve lazy-loaded maintenance centers and hidden child processes

Next: professional UI spacing, DPI scaling and responsive layout polish.

## Current Stabilization Priority — Bunch 6

Status: COMPLETED AFTER TEST PASS.

- Improve Windows DPI rendering
- Apply adaptive Tk scaling
- Make primary panel widths responsive
- Remove conflicting window-size constraints

Next: operator workflow dialogs, loading feedback and error-message polish.

## Current Stabilization Priority — Bunch 7

Status: COMPLETED AFTER TEST PASS.

- Improve loading feedback for long-running app actions
- Replace raw technical failures with trader-friendly safe messages
- Preserve callback recovery and paper-only execution locks

Next: final button-by-button operator workflow QA and long-duration smoke.

## Current Stabilization Priority — Bunch 8

Status: COMPLETED AFTER TEST PASS.

- Validate main operator button callbacks
- Validate primary pages and daily workflows
- Run combined app, RC, acceptance and sign-off safety smoke

Next: long-duration app soak and final release freeze/sign-off.

## Current Stabilization Priority — Bunch 9

Status: COMPLETED AFTER TEST PASS.

- Run sustained GUI process-responsiveness checks
- Track peak memory and memory growth
- Re-run permanent safety guards throughout the soak
- Store machine-readable soak evidence

Next: clean release build and final freeze/sign-off.

## Current Stabilization Priority — Bunch 10

Status: COMPLETED AFTER TEST PASS.

- Simplify the main Overview page
- Remove broker cards from the main operator surface
- Center daily-action controls in a single vertical panel
- Keep broker management inside Broker Connect

Next: final clean release build and freeze/sign-off.

## Current Stabilization Priority — Bunch 11

Status: COMPLETED AFTER TEST PASS.

- Remove temporary build and profiling artifacts from the repository
- Preserve them outside the repository for recovery
- Add a clean-workspace release preflight
- Keep the final UI redesign pending for the last UI pass

Next: final UI pass, clean release build and final freeze/sign-off.

## Current Stabilization Priority — Bunch 12

Status: COMPLETED AFTER TEST PASS.

- Add a repeatable windowed one-file desktop launcher build
- Verify the generated EXE against the permanent safety guard
- Install the desktop shortcut against the current EXE
- Keep source fallback available for recovery

Next: final UI pass and final release freeze/sign-off.

## Current Stabilization Priority — Final UI Approval

Status: WAITING FOR OPERATOR VISUAL APPROVAL.

- Rich but uncluttered Overview
- Wide one-by-one action controls
- Broker Connect retained as a separate page
- Detailed status moved into individual centers

Next: final release rebuild, freeze and sign-off.

## Current Stabilization Priority — Trader Report UX

Status: COMPLETED AFTER OPERATOR APPROVAL.

- Present daily results as a readable HTML trader dashboard
- Keep JSON separate for technical audit
- Preserve raw evidence without forcing traders to read it

Next: final release rebuild, freeze and sign-off.

## Current Stabilization Priority — Exact Trader Report

Status: WAITING FOR OPERATOR VISUAL APPROVAL.

- Exact Module 133 daily pack interpretation
- Plain trader meaning instead of internal codes
- Technical JSON kept separate and collapsed

Next: final commit, release rebuild, freeze and sign-off.

## Current Priority — Fresh Bidirectional SMC Paper Verification

Status: CODE REPAIR BUILT; FRESH MARKET-DAY EVIDENCE REQUIRED.

- LONG -> CE BUY paper evaluation
- SHORT -> PE BUY paper evaluation
- NEUTRAL -> NO TRADE
- Historical PE-only artifacts remain unchanged

Next: fresh paper-watch session, trader report review, commit and release freeze.

## Current Priority — Fresh Current-Day Paper Evidence

Status: CURRENT-DAY GUARD IMPLEMENTED; LIVE MARKET-DAY RUN REQUIRED.

- Old reports cannot appear as today's report
- LONG -> CE BUY | SHORT -> PE BUY | NEUTRAL -> NO TRADE
- Fresh NIFTY, CE and PE evidence is required

Next: fresh paper-watch session, report review, commit and freeze.

## Current Priority — Genuine CE/PE Market-Data Pipeline

Status: OPTION-CHAIN DATA-ONLY FOUNDATION IMPLEMENTED; LIVE DATA-ONLY PROBE REQUIRED.

- Phase A: FYERS option-chain snapshot with both CE and PE
- Phase B: selected CE/PE historical 5m candles
- Phase C: truthful recorded-data replay
- Phase D: current-day trader report

No fake option premium data may be generated.

## Current Priority — Visible Broker Authentication

Status: DIRECT FYERS TOKEN-REFRESH ACCESS ADDED.

- One visible app-native button from Broker Connect
- Secure DPAPI token refresh remains unchanged
- No order APIs are enabled

Next: refresh token and verify genuine CE + PE option-chain data.

## Current Priority — Genuine Selected Option History

Status: SELECTED CE/PE HISTORY FOUNDATION IMPLEMENTED; SECURE LIVE DATA-ONLY PROBE REQUIRED.

- Phase A option-chain snapshot: verified
- Phase B selected CE/PE historical 5m foundation: implemented
- Phase C truthful recorded-data replay: not yet wired
- Phase D current-day trader report: not yet generated

No historical candle or paper trade may be fabricated.

## Current Priority — Truthful Current-Day Recorded Replay

Status: RECORDED REPLAY EVALUATION FOUNDATION IMPLEMENTED; SECURE DATA-ONLY PROBE REQUIRED.

- Genuine NIFTY + selected CE + selected PE data
- Bar-by-bar SMC direction evaluation
- No position or PnL fabrication
- App Today Report integration follows visual review

Next: run replay probe, inspect report, then wire it into Today Report.

## Current Priority — App-Native Recorded Replay Evidence

Status: IMPLEMENTED; OPERATOR VISUAL REVIEW REQUIRED.

- Prefer verified current-day recorded replay over stale daily output
- Show LONG/SHORT/NEUTRAL and CE/PE evaluation counts
- Keep execution and P&L claims blocked
- Preserve the current-day stale-report guard

Next: open HQE App → Today Report and verify the operator view.

## Current Priority — Automatic Daily Report Lifecycle

Status: AUTOMATIC DAILY WORKFLOW IMPLEMENTED; LIVE CURRENT-DAY VERIFICATION REQUIRED.

- App startup automatically starts the data-only daily worker
- During market hours it retries every five minutes
- Current-day replay evidence is published only after all genuine data guards pass
- Today Report remains date-locked and cannot open stale evidence

Next: live current-day automatic run, Today Report visual review, then commit and push.

## Current Priority — Honest Broker/Auth Operator State

Status: TOKEN EXPIRY UI WARNING AND PAPER-WATCH START GATE IMPLEMENTED; VISUAL REVIEW REQUIRED.

- Expired/invalid FYERS token must be explicit on Overview
- Data Ready must never remain visible after an auth failure
- Running process is not equivalent to fresh market-data readiness
- Start Paper Watch fails closed until today's data-only auth path is verified

Next: visual review, token refresh, automatic retry and current-day report verification.

## Current Priority — Deterministic FYERS Auth Recovery

Status: SANITIZED TOKEN-EXCHANGE DIAGNOSTICS IMPLEMENTED; LIVE RETRY REQUIRED.

- Generic exception-only popup replaced with exact safe FYERS code/message
- Full redirect URL paste is accepted
- No credential or token values are printed

Next: perform one fresh authorization exchange and resolve the returned FYERS cause.

## Current Priority — Expiry-Day Data Continuity

Status: EXPIRY-DAY NEXT-WEEK DATA SELECTION IMPLEMENTED; LIVE VERIFICATION REQUIRED.

- Same-day expiry rows are not admitted through the DTE>=1 guard
- The next genuine FYERS-listed weekly expiry is selected automatically
- Existing premium and safety guards are preserved

Next: live workflow completion and Today Report visual review.

## Current Priority — Honest Paper-Watch Runtime State

Status: VERIFIED READY CARD OVERRIDE IMPLEMENTED; VISUAL REVIEW REQUIRED.

- Historical fetch failure is not shown as the current runtime state
- Current-day workflow proof and actual process state remain separate
- READY TO START never means a process is already running

Next: Overview visual approval, then final commit and push.
