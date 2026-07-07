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

## Recorded data paper strategy adapter dry-run consumer

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer.bat

Consumes adapter dry-run events in audit-only paper/simulation mode. This is not a profitability claim.

## Recorded data paper strategy adapter dry-run consumer acceptance gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance.bat

Gates audit-only consumed adapter dry-run events for future consumer evidence. This is not a profitability claim.

## Recorded data paper strategy adapter dry-run consumer readiness gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_readiness.bat

Runs adapter dry-run consumer plus acceptance gate and writes final audit-only consumer readiness. This is not a profitability claim.

## Recorded data paper strategy adapter dry-run consumer evidence bundle

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle.bat

Runs adapter evidence readiness plus consumer readiness and writes final audit-only consumer evidence bundle. This is not a profitability claim.

## Recorded data paper strategy adapter dry-run consumer evidence bundle acceptance gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance.bat

Gates final audit-only consumer evidence bundle for future readiness/release modules. This is not a profitability claim.

## Recorded data paper strategy adapter dry-run consumer evidence readiness gate

Shortcut:

.\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness.bat

Runs consumer evidence bundle plus acceptance and writes final audit-only consumer evidence readiness. This is not a profitability claim.

## v0.5 release command

Main release readiness command:

.\hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness.bat

Release tag:

v0.5-paper-strategy-adapter-consumer-evidence-readiness

This is paper/simulation evidence only and is not a profitability claim.

## Recorded data strategy replay sandbox

Shortcut:

.\hqe_recorded_data_strategy_replay_sandbox.bat

Converts validated recorded-data strategy input bars into strategy replay sandbox events for future decision audit. This is not a profitability claim.

## Recorded data strategy decision audit

Shortcut:

.\hqe_recorded_data_strategy_decision_audit.bat

Converts strategy replay sandbox events into deterministic LONG / SHORT / NEUTRAL decision audit events. This is paper/simulation only and is not a profitability claim.

## Recorded data strategy decision acceptance gate

Shortcut:

.\hqe_recorded_data_strategy_decision_acceptance.bat

Validates LONG / SHORT / NEUTRAL strategy decision audit output before future CE/PE paper trade-plan simulation. This is paper/simulation only and is not a profitability claim.

## Recorded data paper option trade-plan simulator

Shortcut:

.\hqe_recorded_data_paper_option_trade_plan_simulator.bat

Converts accepted LONG / SHORT / NEUTRAL strategy decision audit events into paper-only NIFTY option buy plans. LONG = CE BUY paper plan, SHORT = PE BUY paper plan, NEUTRAL = no trade. This is not a profitability claim.

## Recorded data paper fill and exit simulator

Shortcut:

.\hqe_recorded_data_paper_fill_exit_simulator.bat

Converts CE/PE paper option trade plans into deterministic paper entry/exit lifecycle events. This is paper/simulation only and is not a profitability claim.

## Recorded data backtest trade ledger

Shortcut:

.\hqe_recorded_data_backtest_trade_ledger.bat

Converts paper fill/exit lifecycle records into a paper-only backtest trade ledger. This is not a profitability claim.

## Recorded data backtest metrics engine

Shortcut:

.\hqe_recorded_data_backtest_metrics_engine.bat

Converts paper-only backtest ledger rows into paper-only backtest metrics. This is not a profitability claim.

## Recorded data backtest report writer

Shortcut:

.\hqe_recorded_data_backtest_report_writer.bat

Packages paper-only metrics and trade ledger rows into a readable paper-only backtest report bundle. This is not a profitability claim.

## Recorded data one-command backtest runner

Shortcut:

.\hqe_recorded_data_one_command_backtest_runner.bat

Runs the recorded-data one-command paper backtest chain from replay sandbox through final backtest report writer. This is not a profitability claim.

## Recorded data backtest acceptance gate

Shortcut:

.\hqe_recorded_data_backtest_acceptance_gate.bat

Validates the one-command paper backtest runner output as a paper-only backtest acceptance gate. This is not a profitability claim.

## Recorded data backtest readiness gate

Shortcut:

.\hqe_recorded_data_backtest_readiness_gate.bat

Runs the one-command paper backtest runner and backtest acceptance gate into a paper-only backtest readiness report. This is not a profitability claim.

## v0.6 recorded-data backtest readiness release

Release tag:
v0.6-recorded-data-backtest-readiness

Release note:
docs/V0_6_RECORDED_DATA_BACKTEST_READINESS_RELEASE.md

Primary readiness shortcut:

.\hqe_recorded_data_backtest_readiness_gate.bat

This closes the one-command paper backtest readiness chain. This is not a profitability claim.

## v1.0 Testing Edition release gate

Shortcut:

.\hqe_v1_testing_release_gate.bat

Validates recorded-data backtest readiness evidence before the final paper-only v1.0 Testing Edition release close. This is not a profitability claim.

## v1.0 Testing Edition operator handoff pack

Shortcut:

.\hqe_v1_testing_operator_handoff_pack.bat

Builds the final paper-only v1.0 Testing Edition operator handoff pack before release notes. This is not a profitability claim.

## v1.0 Testing Edition release notes pack

Shortcut:

.\hqe_v1_testing_release_notes.bat

Builds paper-only v1.0 Testing Edition release notes evidence before the release-candidate gate. This is not a profitability claim.

## v1.0 Testing Edition release candidate gate

Shortcut:

.\hqe_v1_testing_release_candidate_gate.bat

Validates paper-only v1.0 Testing Edition release notes evidence before final release close. This is not a profitability claim.

## v1.0 Testing Edition release

Release tag:
v1.0-testing-edition

Release note:
docs/V1_0_TESTING_EDITION_RELEASE.md

Final release-candidate shortcut:

.\hqe_v1_testing_release_candidate_gate.bat

This closes the paper-only v1.0 Testing Edition path. This is not a profitability claim.

## Real dataset backtest input pack

Shortcut:

.\hqe_real_dataset_backtest_input_pack.bat

Discovers saved recorded-data files and writes the first real recorded-data paper backtest input pack. This is not a profitability claim.

## First real dataset backtest run pack

Shortcut:

.\hqe_first_real_dataset_backtest_run_pack.bat

Builds an operator-safe first real recorded-data paper backtest run pack from the real dataset input pack. This is not a profitability claim.

## First real backtest output verification pack

Shortcut:

.\hqe_first_real_backtest_output_verification_pack.bat

Verifies expected paper backtest outputs after the first real recorded-data backtest run. This is not a profitability claim.

## First real backtest report review pack

Shortcut:

.\hqe_first_real_backtest_report_review_pack.bat

Builds an operator review pack for first real recorded-data paper backtest report, metrics, ledger, readiness, release gate, and handoff evidence. This is not a profitability claim.

## Strategy tuning baseline pack

Shortcut:

.\hqe_strategy_tuning_baseline_pack.bat

Builds safe paper-only strategy tuning baseline questions from first real backtest report review evidence. This is not a profitability claim.
