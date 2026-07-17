# HQE Multi-Strategy Phase 4M — Disabled Cutover-Readiness Certificate

## Purpose

Phase 4M binds the reviewed current-SMC selection, one-active invariant,
disabled canonical lifecycle plan, and Phase 4L read-only reconciliation into
one immutable evidence certificate.

The certificate can state that evidence is internally ready for a later human
cutover review. It cannot activate a strategy, switch a strategy, write
selection/state/ledger artifacts, control the canonical runtime, execute a
broker order, or authorize real money.

## Certificate statuses

- `READY_FLAT_DISABLED`: evidence chain is consistent, canonical and sandbox
  lifecycle evidence match at `FLAT`, and all activation/cutover controls remain
  disabled.
- `BLOCKED_OPEN_POSITION`: lifecycle evidence is matched but not flat.
- `BLOCKED_RUNTIME_ACTIVE`: canonical runtime evidence is active.
- `BLOCKED_RECONCILIATION`: lifecycle, position, ledger, or evidence
  reconciliation is not a flat match.
- `BLOCKED_EVIDENCE`: the disabled lifecycle plan or operator recommendation is
  not ready.
- `BLOCKED_IDENTITY`: evidence hashes or strategy identity do not form one
  consistent chain.

## Bound evidence

The certificate records hashes for:

- selected strategy snapshot;
- one-active strategy set;
- disabled lifecycle plan;
- disabled activation preflight embedded by the lifecycle plan;
- Phase 4L reconciliation result and operator view;
- Phase 4K sandbox bundle;
- canonical Module 131 migration plan and read-only evidence files.

## Zero-authority boundary

Every certificate and operator-view control remains `false`:

- activation;
- strategy switch and selection write;
- lifecycle/state/ledger write;
- runtime connection/control/cutover;
- broker execution;
- real money.

Phase 4M does not persist the certificate into canonical runtime directories and
does not modify Product UI, licensing, broker adapters, or the existing
paper-only release freeze manifest.

## Exit gate

Phase 4M passes only when:

1. the exact Phase 4I–4L pending file hashes are unchanged;
2. focused certificate tests pass;
3. cumulative multi-strategy and critical regression passes;
4. the offline dry-run produces `READY_FLAT_DISABLED`;
5. open-position, divergence, identity-tamper, and runtime-active probes are
   fail-closed;
6. canonical evidence hashes remain identical before and after certification;
7. no activation, canonical write, broker, real-money, commit, or push action is
   performed.

## Next core path

The next step is a read-only operator cutover checklist and evidence bundle
export model. It must still carry zero activation authority.
