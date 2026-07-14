# Hunter Quant Engine — Paper-Only RC Operator Guide

## Normal daily workflow

Open **Hunter Quant Engine** from the Windows desktop shortcut.

Use the app in this order:

1. **Operator Dashboard**
2. **Connect / Market Data**
3. **Prepare**
4. **Paper Watch**
5. **Daily Close**
6. **Paper Validation Intelligence**
7. **Session History / Reports**

## Strategy and backtest workflow

1. Open **Strategy Pack Center** to review existing packs.
2. Open **Strategy Builder & Selector** to create a paper-only draft.
3. Preview and validate the draft.
4. Select a valid pack only for paper validation.
5. Open **Backtest Product Center**.
6. Select quality-approved recorded data and a strategy pack.
7. Preview the backtest job.
8. Run only when a compatible guarded recorded-data runner is available.
9. Review result metrics and equity/drawdown evidence.

HQE does not fabricate option prices.

## Validation workflow

Paper validation remains locked to the approved candidate unless a formal
review changes it.

Minimum evidence thresholds:

- 20 observed days
- 30 observed paper trades
- 4 observed expiry weeks

`READY_FOR_FORMAL_REVIEW` does not approve real trading.

## Backup and diagnostics

Use **Windows Release Center** to:

- Create a user backup
- Stage a restore from backup
- Create a diagnostics bundle
- Install the desktop shortcut
- Run a release-candidate guard dry run

Restore staging never overwrites live workspace files automatically.

## Final RC audit

Open **Final RC Audit & Freeze** and run the end-to-end RC audit.

Blocking failures include:

- Missing release files
- Failed component guards
- Unsafe app-layer execution calls
- Invalid launcher assets
- Freeze-manifest hash mismatches
- Unwritable workspace

Snapshot items may show `CHECK_REQUIRED` when current market or validation
evidence is incomplete. Review those items without inventing data.

## Permanent safety

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO
- Option selling: NO
- Fake trades: NO

This is not a profitability claim.

## Advanced Tools and Product Centers

From the Overview page, use **Advanced Tools & Product Centers**.

The scrollable hub provides direct access to:

- Operator Dashboard
- Market Data Quality Center
- Strategy Pack Center
- Strategy Builder & Selector
- Backtest Product Center
- Session History
- Paper Validation Intelligence
- Windows Release Center
- Final RC Audit & Freeze
- Operator Acceptance & RC Sign-Off

Daily market use normally requires Overview, Broker Connect, Paper Watch,
Today Report and System Safety. Release/audit centers are maintenance tools.

### Advanced-center loading behavior

Advanced and maintenance centers are lazy-loaded. They do not run heavy
status scans during normal HQE startup.

Open **Advanced Tools & Product Centers**, then select the required center.
This keeps desktop launch fast and prevents terminal-window flashes.
A failed UI action displays an error dialog and writes a diagnostic log
instead of leaving a blank window.

## Trader Overview and Sidebar Categories V2

Overview daily controls:

- Refresh Status
- Start Paper Trading
- Stop Paper Trading
- Open Daily Report

Additional controls are grouped under Broker Connect, Paper Watch, Daily Operations, Reports & Evidence, System Safety and Advanced Tools.

Embedded Live Status remains at the bottom. Green Internet and Paper Watch cards indicate that the paper-only watcher is running with Internet online. Green status does not enable real broker execution.
