# HQE Current-Day Data and Watch Repair V1

This module provides one unified truth for:

- current IST trading date,
- FYERS authentication response,
- current-day candle presence,
- candle freshness,
- actual Python paper-watch process,
- canonical watch PID,
- operator recommendation.

It performs a current-day data-only fetch, writes mapped candles atomically, starts the paper-only watch when absent, and writes a unified repair status.

No real orders, broker execution, auto trading, or option selling are enabled.

This is not a profitability claim.
