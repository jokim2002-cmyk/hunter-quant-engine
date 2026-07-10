# HQE Fyers Fetch Evidence Truth V1

This audit separates reported fetch completion from actual candle freshness.

It verifies the reported Fyers fetch status, latest candle timestamp, candle age during market hours, canonical parent watch PID, process count, and operator recommendation.

Possible truth states:

- `LIVE_DATA_FRESH`
- `FETCH_COMPLETED_BUT_CANDLE_STALE`
- `FETCH_COMPLETED_BUT_NO_CANDLE_DATA`
- `FETCH_FAILED`
- `WATCH_PROCESS_STOPPED`
- `MARKET_CLOSED_IDLE`

No automatic restart or broker execution is performed.

Safety:

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO

This is not a profitability claim.
