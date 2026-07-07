# HQE Shortcuts

This document lists operator shortcuts for paper/simulation evidence workflows.

## Recorded data replay dataset

Shortcut:

.\hqe_recorded_data_replay_dataset.bat

Builds a paper/simulation-only normalized replay dataset report from recorded-data inventory/discovery. Outputs are generated under reports\paper_trading\recorded_data_replay_dataset and must not be committed. This is not a profitability claim.

## Recorded data replay quality gate

Shortcut:

.\hqe_recorded_data_replay_quality_gate.bat

Audits the normalized replay dataset created by Module O and writes paper/simulation-only quality-gate reports under reports\paper_trading\recorded_data_replay_quality_gate. This is not a profitability claim.

## Recorded data replay dry-run

Shortcut:

.\hqe_recorded_data_replay_dry_run.bat

Converts normalized recorded-data replay records into a deterministic paper/simulation-only dry-run event stream under reports\paper_trading\recorded_data_replay_dry_run. This is not a profitability claim.

## Recorded data replay evidence bundle

Shortcut:

.\hqe_recorded_data_replay_evidence.bat

Runs the recorded-data replay dataset normalizer, quality gate, dry-run player, and combined paper/simulation-only evidence summary. This is not a profitability claim.

## Recorded data replay acceptance gate

Shortcut:

.\hqe_recorded_data_replay_acceptance.bat

Gates the recorded-data replay evidence bundle for future paper/simulation replay readiness using required stages, warning policy, and minimum event count. This is not a profitability claim.

## Recorded data replay readiness gate

Shortcut:

.\hqe_recorded_data_replay_readiness.bat

Runs the recorded-data replay evidence bundle plus acceptance gate and writes a final paper/simulation-only readiness report. This is not a profitability claim.

## Recorded data strategy input contract

Shortcut:

.\hqe_recorded_data_strategy_input_contract.bat

Converts recorded-data replay dry-run events into a future paper-strategy input contract while blocking execution/trading/profit fields. This is not a profitability claim.

## Recorded data strategy replay preflight

Shortcut:

.\hqe_recorded_data_strategy_replay_preflight.bat

Runs replay readiness plus strategy input contract and writes a final paper/simulation-only preflight report for future paper strategy replay. This is not a profitability claim.

## Recorded data strategy replay scenario manifest

Shortcut:

.\hqe_recorded_data_strategy_replay_scenario.bat

Packages accepted recorded-data strategy input bars into deterministic future paper replay scenarios. This is not a profitability claim.

## Recorded data strategy replay scenario acceptance gate

Shortcut:

.\hqe_recorded_data_strategy_replay_scenario_acceptance.bat

Gates recorded-data strategy replay scenarios for future paper/simulation replay readiness using minimum scenario/bar rules and warning policy. This is not a profitability claim.

## Recorded data strategy replay scenario readiness gate

Shortcut:

.\hqe_recorded_data_strategy_replay_scenario_readiness.bat

Runs future paper strategy replay preflight, scenario manifest, scenario acceptance, and final paper/simulation-only scenario readiness report. This is not a profitability claim.
