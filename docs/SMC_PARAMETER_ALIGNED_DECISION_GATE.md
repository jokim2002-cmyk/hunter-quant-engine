# SMC Parameter-Aligned Decision Gate

This patch fixes the paper backtest overtrading root cause.

Old behavior:

- close-to-close movement generated LONG/SHORT decisions
- threshold default was 0.0
- almost every candle became a trade candidate

New behavior:

- LONG/SHORT require SMC confluence from recorded OHLC bars
- liquidity sweep evidence is required
- market structure break evidence is required
- entry-zone evidence via FVG/displacement proxy is required
- otherwise decision is NEUTRAL and no CE/PE paper trade plan is created

Safety:

- Paper/simulation only
- No broker connection
- No live market data
- No real orders
- No real money
- Not a profitability claim
