# HQE Final Persistent Watch Live-Data Repair V1

The persistent paper watch now routes data fetches through a safe current-day live-data cycle.

The cycle forces the current IST trading date, passes `--execute-live-data-only`, requires API code 200 and positive rows, writes candles atomically, and preserves the last known good CSV on authentication, API, zero-row, or writer failure.

Sample-schema overwrite during a market watch is blocked.

Safety remains paper/data only. No real orders, broker execution, or auto trading are enabled.

This is not a profitability claim.
