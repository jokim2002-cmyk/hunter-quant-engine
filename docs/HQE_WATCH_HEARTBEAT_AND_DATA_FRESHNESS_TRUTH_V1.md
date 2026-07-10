# HQE Watch Heartbeat and Data Freshness Truth V1

This module separates process liveness from actual data health.

Possible health states:

- `HEALTHY`
- `DEGRADED_DATA_STALE`
- `STOPPED`
- `MARKET_CLOSED_IDLE`

Evidence includes:

- heartbeat timestamp in IST,
- Paper Watch PID,
- last successful data-update timestamp,
- data age,
- consecutive stale-cycle count,
- latest data file,
- fetch failure reason.

Safety remains fixed:

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO

This is not a profitability claim.
