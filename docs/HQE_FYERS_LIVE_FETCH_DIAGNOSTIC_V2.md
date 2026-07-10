# HQE Fyers Live Fetch Diagnostic V2

This repair makes live-fetch evidence strict.

A successful decision now requires:

- an explicit live data-only flag,
- external API execution proof,
- history execution proof,
- returned row count greater than zero,
- semantic CSV change by SHA-256, row count, or latest candle timestamp.

Offline sample rewrites and modification-time-only changes are rejected.

The watch-process query accepts only actual Python executables.

Safety remains:

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO

This is not a profitability claim.
