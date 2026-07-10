# HQE App V2 Public Trader UI and Multi-Broker Architecture Pack

## Scope

This pack implements the next roadmap build without changing the locked
real-trading status.

## Included

- Modern public trader desktop UI
- Internet status
- Selected broker status
- Market-data status
- Paper-watch status
- Hidden background paper-watch process
- Today Report viewer
- Broker cards for:
  - Fyers
  - Zerodha
  - Angel One
  - Upstox
  - Groww
  - Dhan
- Common data-only broker adapter contract
- Redacted credential readiness model
- Architecture and safety guard tests

## Broker implementation status

Fyers continues to use the existing HQE data-only scripts and evidence files.

Zerodha, Angel One, Upstox, Groww and Dhan currently have architecture-ready
registry entries only. Their real network adapters are not yet implemented.

No broker in this pack has order execution methods.

## Daily public usage

The public trader launches HQE App V2 and uses the app buttons.

The hidden paper-watch controller launches the existing persistent paper-watch
Python process without opening a visible terminal window.

CMD and PowerShell remain internal development and installation tools only.

## Safety lock

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO
- Option selling: NO
- Fake trades: NO
- Profitability claim: NO
- Paper/data-only operation: YES

This is not a profitability claim.
