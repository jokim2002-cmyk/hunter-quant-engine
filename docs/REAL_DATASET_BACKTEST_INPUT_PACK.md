# Real Dataset Backtest Input Pack

Module LLL starts the post-v1.0 Real Backtest Usage Sprint.

Purpose:
The real dataset backtest input pack discovers saved recorded-data files and writes a safe operator pack for the first real recorded-data paper backtest run.

Command:
.\scripts\paper_trading\hqe_real_dataset_backtest_input_pack.bat

Default input directories:
- data\recorded
- data\live_recording

Default output:
reports\paper_trading\real_dataset_backtest_input_pack

Generated files:
- real_dataset_backtest_input_pack.json
- real_dataset_backtest_input_pack.txt
- real_dataset_backtest_commands.txt
- manifest.json

Supported dataset file types:
- .csv
- .json
- .jsonl
- .parquet

Suggested run order after a dataset is present:
- .\scripts\paper_trading\hqe_recorded_data_inventory.bat
- .\scripts\paper_trading\hqe_recorded_data_replay_dataset.bat
- .\scripts\paper_trading\hqe_recorded_data_replay_quality_gate.bat
- .\scripts\paper_trading\hqe_recorded_data_backtest_readiness_gate.bat
- .\scripts\paper_trading\hqe_v1_testing_release_gate.bat
- .\scripts\paper_trading\hqe_v1_testing_operator_handoff_pack.bat

Safety:
- LONG = CE BUY paper plan only.
- SHORT = PE BUY paper plan only.
- NEUTRAL = no trade.
- No option selling.
- No broker orders.
- No live market data.
- No real money.

Safety boundary:
This is a paper-only real dataset backtest input pack. It does not connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.

Progress:
- v1.0 Testing Edition: 63/63 modules complete.
- v1.0 pending: 0 modules.
- Completed total before Module LLL: 63 modules.
- Phase 1 pending before Module LLL: 10 modules.
- Phase 1 pending after Module LLL: 9 modules.
- Full HQE product estimate after Module LLL: 56-61%.
