# HQE Multi-Strategy Phase 4 Complete Forward-Paper Integration

## Status

Phase 4 implementation is complete as one cohesive coding bunch.

The canonical paper runtime can now route the reviewed current SMC strategy
through a one-active-strategy namespaced lifecycle after an explicit human
paper-only gate is present. Without that gate, the released legacy runtime path
continues unchanged.

## Implemented scope

- explicit deterministic human cutover gate
- reviewed current-SMC identity and parameter binding
- one-active-strategy canonical selection evidence
- atomic legacy Module 131 state/ledger/evidence migration
- legacy source preservation during initial migration
- per-strategy state, ledger, summary, report and reason-log namespace
- canonical runtime path routing through the selected namespace
- existing OPEN-position migration without data loss
- restart recovery through the namespaced Module 131 state
- runtime-running strategy-switch guard
- open-position strategy-switch guard
- unreviewed strategy activation guard
- initial legacy/namespaced reconciliation
- flat-and-stopped rollback with legacy synchronization and backup
- runtime status and Today Report strategy identity evidence
- isolated full OPEN to CLOSED paper lifecycle rehearsal

## Runtime layout

The control plane remains discoverable at:

```text
<workspace>/HQE_PAPER_PRODUCT_RUNTIME/
  HQE_PAPER_PRODUCT_RUNTIME.json
  HQE_PAPER_PRODUCT_RUNTIME.log
  HQE_PAPER_PRODUCT_STOP.flag
```

After a valid human gate, Module 131 evidence is routed to:

```text
<workspace>/HQE_PAPER_PRODUCT_RUNTIME/
  strategies/
    hqe_current_smc_compatibility/
      1.0.0/
        <parameters_hash>/
          selection.json
          MODULE_131_POSITION_STATE.json
          MODULE_131_PAPER_LEDGER.csv
          MODULE_131_SUPERVISOR_SUMMARY.json
          MODULE_131_INTRADAY_SUPERVISOR_REPORT.md
          MODULE_131_SIGNAL_REASON_LOG.csv
          HQE_MULTI_STRATEGY_PHASE4_MIGRATION.json
          HQE_MULTI_STRATEGY_PHASE4_RECONCILIATION.json
```

## Human gate

The runtime remains in legacy compatibility mode until the exact gate exists:

```text
HQE_MULTI_STRATEGY_PHASE4_HUMAN_GATE.json
```

Required approval phrase:

```text
APPROVE PAPER-ONLY CURRENT SMC CUTOVER
```

The gate is bound to the reviewed strategy ID, version, implementation key,
manifest fingerprint, parameters hash, selection hash and permanent safety
flags. Any tampering fails closed.

The Phase 4 installation and test script does not create this gate in the
user's real product workspace. The isolated rehearsal creates it only inside a
dedicated test workspace.

## Migration and recovery

Initial cutover requires the runtime to be stopped. Existing legacy Module 131
state, ledger, summary, report and reason log are copied atomically into the
strategy namespace. Original legacy files remain untouched during the
namespaced run.

An existing OPEN paper position is preserved exactly. Restart recovery reads
the namespaced state after the gate is active.

Rollback is allowed only when:

- the runtime is stopped
- the namespaced position is FLAT

Rollback synchronizes namespaced evidence back to the legacy location, creates
a backup, disables the gate and preserves the namespaced evidence.

## Permanent safety boundary

This phase does not add or authorize:

- real orders
- broker order execution
- auto trading
- real money
- option selling
- unrestricted imported strategy activation
- silent strategy switching
- Product UI strategy-manager controls
- license or Machine ID changes
- master merge

Only the reviewed current SMC compatibility strategy can use the canonical
Phase 4 gate. Additional strategies require later reviewed phases.

## Validation

The combined Phase 4 gate requires:

- focused canonical integration tests
- existing paper-product and Module 131 regression tests
- cumulative multi-strategy and critical regression
- environment-dependent recovery tests
- full functional regression
- exact four deferred release/freeze gates only
- isolated flat lifecycle and open-state migration rehearsal
- protected master and product safety verification

## Next roadmap phase

Phase 5: complete Product UI Strategy Manager bunch.

The UI phase will expose available/selected strategy identity, version,
parameters, validation, safe selection and open-position protection. It must use
the Phase 4 gate and integration APIs rather than rewriting the paper runtime.
