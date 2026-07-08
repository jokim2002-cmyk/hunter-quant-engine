# Recorded Data Replay Acceptance Gate

Module S adds a paper/simulation-only acceptance gate for the recorded-data replay evidence bundle.

Purpose:
The gate reads the combined replay evidence summary from Module R and decides whether the bundle is structurally acceptable for a future paper/simulation strategy replay phase.

Default input:
reports\paper_trading\recorded_data_replay_evidence\evidence_summary.json

Default output folder:
reports\paper_trading\recorded_data_replay_acceptance

Generated files:
- acceptance_gate.json
- acceptance_gate.txt
- manifest.json

Command:
.\hqe_recorded_data_replay_acceptance.bat

Optional minimum event rule:
.\hqe_recorded_data_replay_acceptance.bat --min-events 100

Optional warning policy:
.\hqe_recorded_data_replay_acceptance.bat --allow-warnings

Checks:
- evidence summary exists and is valid JSON
- required replay stages are present
- required replay stages are pass unless warnings are explicitly allowed
- bundle status is pass unless warnings are explicitly allowed
- replay dry-run event count meets the configured minimum

Safety boundary:
This module is paper/evidence only. It does not run strategies, create trade plans, connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
