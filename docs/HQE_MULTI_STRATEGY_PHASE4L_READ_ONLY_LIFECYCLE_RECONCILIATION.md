# HQE Multi-Strategy Phase 4L — Read-Only Lifecycle Reconciliation

## Scope

Phase 4L compares the guarded Phase 4K namespaced lifecycle bundle with the
existing canonical current-SMC Module 131 lifecycle evidence. Both sides are
read-only inputs. This phase does not repair, copy, migrate, activate, switch,
or cut over any runtime file.

## Semantic comparison

The reconciliation intentionally compares lifecycle meaning rather than file
format:

- final lifecycle (`FLAT` or open-position semantic `OPEN`),
- open/close/unmatched position balance,
- option side, symbol, quantity, and entry while a position is open,
- stable SHA-256 identities of canonical evidence,
- the tamper-evident sandbox bundle hash.

`HELD` in the namespaced lifecycle is compared to canonical `OPEN`, because the
legacy Module 131 state represents an actively held position as `OPEN`.

## Fail-closed statuses

- `MATCH_FLAT`
- `MATCH_OPEN`
- `DIVERGED_LIFECYCLE`
- `DIVERGED_POSITION`
- `DIVERGED_LEDGER`
- `BLOCKED_RUNTIME_RUNNING`
- `BLOCKED_CANONICAL_EVIDENCE`
- `NO_CANONICAL_EVIDENCE`

A match is evidence only. It does not authorize strategy switching, lifecycle
writes, runtime cutover, broker execution, real orders, or real money.

## Protected boundary

- canonical Module 131 evidence: read-only
- Phase 4K sandbox bundle: read-only
- Product UI: unchanged
- canonical paper runtime: unchanged
- licensing and Machine ID: unchanged
- commit and push: not performed

## Next path

After exact reconciliation evidence is stable, add a disabled cutover-readiness
certificate that still cannot activate or write canonical runtime files.
