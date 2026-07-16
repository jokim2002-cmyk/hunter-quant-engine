# HQE Multi-Strategy Phase 4G — Disabled Activation Preflight and UI Model

## Scope

Phase 4G evaluates whether the existing offline evidence set is internally
ready for a later activation review. It does **not** activate a strategy or
connect the canonical product runtime.

It also creates a display-only product strategy model. The model is not wired
into `hqe_product_app_v2.py`; it contains no callbacks or commands.

## Preflight result

The preflight can report:

- `READY_DISABLED`
- `BLOCKED_RUNTIME_ACTIVE`
- `BLOCKED_EVIDENCE`

`READY_DISABLED` means only that the evidence is internally consistent while
activation remains locked. Every authorization flag is permanently false.

## Required evidence

- reviewed manifest identity equals the disabled selection
- recovery is `READY_FLAT`
- operator evidence is `PASS_CLOSED`
- zero mismatches
- minimum parity-cycle count is satisfied
- LONG, SHORT and NEUTRAL were observed
- CE_BUY, PE_BUY and NO_TRADE were observed
- latest stable runtime observation is STOPPED or NOT_FOUND

## Product UI model

The read-only model exposes:

- strategy name, ID and version
- implementation key and manifest fingerprint
- parameter snapshot
- selection, preflight, recovery and evidence hashes
- runtime observation status
- parity counts and blockers

The following remain disabled:

- strategy selection
- activation
- start and stop
- runtime control
- lifecycle/state/ledger writes
- broker execution
- real money

## Protected boundaries

This phase does not edit:

- canonical Product UI
- product runtime
- forward paper supervisor
- Module 131 state, ledger or reports
- licensing or Machine ID
- backtest engine or pipeline
