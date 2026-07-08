# Recorded Data Paper Strategy Adapter Contract Acceptance Gate

Module EE adds a paper/simulation-only acceptance gate for the adapter contract from Module DD.

Purpose:
The gate reads the adapter contract and decides whether its adapter requests are structurally acceptable for a future paper/simulation adapter dry-run phase.

Command:
.\scripts\paper_trading\hqe_recorded_data_paper_strategy_adapter_contract_acceptance.bat

Default input:
reports\paper_trading\recorded_data_paper_strategy_adapter_contract\paper_strategy_adapter_contract.json

Default output:
reports\paper_trading\recorded_data_paper_strategy_adapter_contract_acceptance

Generated files:
- paper_strategy_adapter_contract_acceptance.json
- paper_strategy_adapter_contract_acceptance.txt
- manifest.json

Safety boundary:
This module is paper/evidence only. It does not execute strategy logic, create signals, create trade plans, connect to a broker, request live market data, place real orders, use real money, calculate PnL, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
