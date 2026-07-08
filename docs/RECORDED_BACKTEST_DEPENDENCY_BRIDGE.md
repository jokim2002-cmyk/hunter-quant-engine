# Recorded Backtest Dependency Bridge

This module fixes the recorded-data paper backtest dependency gap where the strategy replay sandbox requires paper strategy adapter consumer evidence readiness, while the adapter replay-plan chain can produce zero adapter requests.

The bridge derives the required consumer evidence readiness from the already validated strategy input contract and strategy input bars.

Safety scope:

- Paper/simulation evidence only.
- No broker connection.
- No live market data request.
- No real orders.
- No real money.
- No profitability claim.

Primary shortcut:

.\hqe_recorded_data_backtest_dependency_bridge.bat
