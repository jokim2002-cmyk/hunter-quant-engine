# Paper Session and Trade Frequency Filter Review Pack

Module ZZZZ continues the post-v1.0 Paper Improvement Execution Sprint.

Command:

```bat
.\scripts\paper_trading\hqe_paper_session_trade_frequency_filter_review_pack.bat
```

Purpose:
This pack reviews session-window, daily concentration, and trade-frequency
assumptions before any future improved recorded-data paper rerun.

Default inputs:
- `reports\paper_trading\paper_tuning_candidate_readiness_pack\paper_tuning_candidate_readiness_pack.json`
- `reports\paper_trading\paper_signal_cooldown_duplicate_filter_review_pack\paper_signal_cooldown_duplicate_filter_review_pack.json`
- `reports\paper_trading\paper_trade_frequency_guard\paper_trade_frequency_guard.json`

Default output:
`reports\paper_trading\paper_session_trade_frequency_filter_review_pack`

Generated files:
- `paper_session_trade_frequency_filter_review_pack.json`
- `paper_session_trade_frequency_filter_review_pack.txt`
- `paper_session_trade_frequency_filter_review_items.csv`
- `manifest.json`

Safety:
- LONG = CE BUY paper plan only.
- SHORT = PE BUY paper plan only.
- NEUTRAL = no trade.
- No option selling.
- No futures/equity execution.
- No broker orders.
- No live market data.
- No real money.
- Strategy logic is not changed.
- No backtest is executed by this pack.
- This is not a profitability claim.

Progress:
- v1.0 Testing Edition: 63/63 modules complete.
- Phase 1 Real Backtest Usage Sprint complete.
- Phase 2 Dashboard Sprint complete.
- Phase 3 Recorded Backtest Review Workflow complete.
- Phase 4 Paper Backtest Evidence Analysis Sprint complete.
- Phase 5 Paper Improvement Readiness Sprint complete.
- Phase 6 Paper Improvement Execution Sprint continues.
- Completed total before Module ZZZZ: 103 modules.
- Completed total after Module ZZZZ: 104 modules.
- Phase 6 pending after Module ZZZZ: 1 module.
- Full HQE product estimate after Module ZZZZ: 95-99%.
