# Recorded Data Paper Strategy Adapter Dry-Run Consumer

Module NN adds a paper/simulation-only adapter dry-run consumer scaffold.

Purpose:
The consumer reads adapter evidence readiness plus adapter dry-run events, then consumes those events in audit-only mode.

Command:
.\scripts\paper_trading\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer.bat

Default inputs:
reports\paper_trading\recorded_data_paper_strategy_adapter_evidence_readiness\paper_strategy_adapter_evidence_readiness.json
reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run\paper_strategy_adapter_dry_run_events.jsonl

Default output:
reports\paper_trading\recorded_data_paper_strategy_adapter_dry_run_consumer

Generated files:
- paper_strategy_adapter_dry_run_consumer.json
- paper_strategy_adapter_dry_run_consumed_events.jsonl
- paper_strategy_adapter_dry_run_consumer.txt
- manifest.json

Safety boundary:
This module is paper/evidence only. It does not execute strategy logic, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
