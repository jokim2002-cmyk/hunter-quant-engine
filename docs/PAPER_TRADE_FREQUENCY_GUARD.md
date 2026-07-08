# Paper Trade Frequency Guard

This module fixes the paper backtest overtrading symptom where baseline recorded-data output can produce nearly one trade per candle.

Guard rules:

- one-position-at-a-time behavior
- cooldown after exit
- duplicate same-direction filter
- max trades per day
- paper-only safety fields must remain disabled

Default settings:

- cooldown bars after exit: 3
- bar minutes: 5
- max trades per day: 6
- require direction change: true

Safety scope:

- Paper/simulation only.
- No broker connection.
- No live market data.
- No real orders.
- No real money.
- No profitability proof.

Shortcut:

.\scripts\paper_trading\hqe_paper_trade_frequency_guard.bat
