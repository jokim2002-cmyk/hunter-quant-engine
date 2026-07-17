# HQE Multi-Strategy Phase 4K — Guarded Namespaced Lifecycle Write Sandbox

## Status

Phase 4K is an isolated write-sandbox milestone for the reviewed current SMC
compatibility strategy. It does **not** connect to the canonical product paper
runtime and does **not** authorize activation, strategy switching, broker
execution, real orders, or real money.

## Purpose

Phase 4J proved the one-active strategy invariant and projected the canonical
`FLAT → OPEN → HELD → CLOSED → FLAT` lifecycle without writes. Phase 4K adds a
strictly namespaced sandbox where those transitions can be written and recovered
without touching canonical Module 131 state, canonical ledgers, Product UI, or
runtime control files.

## Guarded permit

A sandbox write permit is issued only when all of these are true:

- the Phase 4J lifecycle plan is `READY_DISABLED`;
- the selected strategy is the reviewed current SMC compatibility strategy;
- exactly one strategy is selected;
- the current lifecycle is `FLAT`;
- the sandbox root uses the explicit `HQE_MULTI_STRATEGY_PHASE4K_SANDBOX`
  prefix;
- the sandbox root does not overlap the read-only canonical evidence namespace;
- canonical selection/state/ledger writes remain disabled;
- runtime cutover, broker execution, and real money remain disabled.

## Authoritative bundle and projections

Each strategy/parameter namespace contains:

- `lifecycle_bundle.json` — authoritative atomic bundle with current state and a
  tamper-evident event hash chain;
- `selection.json` — sandbox-only selection projection;
- `state.json` — sandbox-only current-state projection;
- `ledger.csv` — sandbox-only lifecycle ledger projection.

The bundle is written using a same-directory temporary file and `os.replace`.
Projection failures trigger process-level rollback to the prior bundle and prior
projections. The bundle can also repair projections deterministically.

## Write guards

- exclusive per-namespace write lock;
- stale before-state rejection;
- duplicate event-ID rejection;
- selection and parameter identity lock;
- lifecycle transition validation through the Phase 4J adapter;
- option side/symbol continuity while a position remains open;
- event hash chain and state hash chain verification;
- current reviewed SMC identity only.

## Explicit non-goals

Phase 4K does not:

- modify `scripts/hqe_product_app_v2.py`;
- modify `scripts/hqe_paper_product_runtime.py`;
- modify `scripts/run_forward_intraday_paper_supervisor.py`;
- modify canonical Module 131 state or ledger files;
- activate or switch a strategy;
- import package payload code;
- place broker orders;
- use real money;
- modify licensing or Machine ID logic;
- refresh the old paper-only release freeze manifest.

## Exit gate

Phase 4K closes only when targeted tests, cumulative regression, the offline
four-transition write dry-run, stale/duplicate/concurrent-write guards, exact
Git scope, and all protected-source checks pass.

## Next core path

After Phase 4K, the next guarded milestone is read-only reconciliation between
the namespaced sandbox bundle and canonical current-SMC lifecycle evidence.
Canonical runtime cutover remains disabled.
