# HQE Backtest Product Center Bunch

This cohesive roadmap bunch combines:

1. Dataset selection from the market-data quality layer
2. Strategy-pack selection
3. Date-range controls
4. Initial-capital, brokerage, slippage, taxes and trade-limit controls
5. Backtest-job schema and validation
6. Guarded existing-runner discovery and command construction
7. Hidden background backtest jobs
8. Result normalization from JSON/CSV outputs
9. Trade count, win rate, gross/net, costs, average trade and drawdown metrics
10. Equity-curve evidence extraction
11. App-native Backtest Product Center

Important integrity rule:

HQE does not fabricate option prices. A run is enabled only when an existing
recorded-data backtest runner exposes a guard-check and compatible safe CLI.
Otherwise the product center blocks the run and still allows job preview/save.

Permanent safety:

- Recorded-data research only: YES
- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO
- Option selling: NO
- Fake trades or prices: NO

This is not a profitability claim.
