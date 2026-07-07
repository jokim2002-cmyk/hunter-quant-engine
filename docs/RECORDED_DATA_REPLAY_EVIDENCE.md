# Recorded Data Replay Evidence Bundle

Module R adds a one-command paper/simulation-only evidence bundle for recorded-data replay readiness.

Purpose:
The bundle runs the replay evidence pipeline end to end:
1. Recorded data replay dataset normalizer.
2. Recorded data replay quality gate.
3. Recorded data replay dry-run player.
4. Combined evidence summary and manifest.

Command:
.\hqe_recorded_data_replay_evidence.bat

Optional custom path example:
.\hqe_recorded_data_replay_evidence.bat --recorded-root data\recorded --base-output-dir reports\paper_trading --output-dir reports\paper_trading\recorded_data_replay_evidence

Optional dry-run record limit:
.\hqe_recorded_data_replay_evidence.bat --max-records 100

Default stage outputs:
- reports\paper_trading\recorded_data_replay_dataset
- reports\paper_trading\recorded_data_replay_quality_gate
- reports\paper_trading\recorded_data_replay_dry_run
- reports\paper_trading\recorded_data_replay_evidence

Safety boundary:
This module is paper/evidence only. It does not run strategies, create trade plans, connect to a broker, request live market data, place real orders, use real money, or prove profitability.

This report is not a profitability claim. Generated reports/data remain ignored and must not be committed.
