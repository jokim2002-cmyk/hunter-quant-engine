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

## Recorded data paper strategy replay plan

Shortcut:

.\hqe_recorded_data_paper_strategy_replay_plan.bat

Builds a no-execution paper/simulation-only replay plan from scenario readiness, scenario manifest, and strategy input bars. This is not a profitability claim.

## Recorded data paper strategy replay plan acceptance gate

Shortcut:

.\hqe_recorded_data_paper_strategy_replay_plan_acceptance.bat

Gates the no-execution recorded-data paper strategy replay plan before any future paper/simulation replay consumer can use it. This is not a profitability claim.

## Recorded data paper strategy replay plan readiness gate

Shortcut:

.\hqe_recorded_data_paper_strategy_replay_plan_readiness.bat

Runs the no-execution replay plan plus acceptance gate and writes final paper/simulation-only plan readiness. This is not a profitability claim.

## Recorded data paper strategy adapter contract

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_contract.bat

Builds no-execution adapter request manifests for future paper strategy replay. This is not a profitability claim.

## Recorded data paper strategy adapter contract acceptance gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_contract_acceptance.bat

Gates no-execution adapter request manifests for future paper strategy adapter dry-run. This is not a profitability claim.

## Recorded data paper strategy adapter readiness gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_readiness.bat

Runs the no-execution adapter contract plus acceptance gate and writes final adapter readiness. This is not a profitability claim.

## Recorded data paper strategy adapter dry-run

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run.bat

Converts no-execution adapter requests into deterministic dry-run events. This is not a profitability claim.

## Recorded data paper strategy adapter dry-run acceptance gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run_acceptance.bat

Gates no-execution adapter dry-run events for future paper adapter evidence. This is not a profitability claim.

## Recorded data paper strategy adapter dry-run readiness gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run_readiness.bat

Runs no-execution adapter dry-run plus acceptance gate and writes final adapter dry-run readiness. This is not a profitability claim.

## Recorded data paper strategy adapter evidence bundle

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_evidence_bundle.bat

Runs adapter readiness plus adapter dry-run readiness and writes a final paper/simulation adapter evidence bundle. This is not a profitability claim.

## Recorded data paper strategy adapter evidence bundle acceptance gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_evidence_bundle_acceptance.bat

Gates final adapter evidence bundle structure for future release/readiness modules. This is not a profitability claim.

## Recorded data paper strategy adapter evidence readiness gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_evidence_readiness.bat

Runs adapter evidence bundle plus acceptance gate and writes final adapter evidence readiness. This is not a profitability claim.

## v0.4 release command

Main release readiness command:

.\hqe_recorded_data_paper_strategy_adapter_evidence_readiness.bat

Release tag:

v0.4-paper-strategy-adapter-evidence-readiness

This is paper/simulation evidence only and is not a profitability claim.
