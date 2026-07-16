# HQE Multi-Strategy Phase 4E — Guarded Shadow Session Journal

## Scope

Phase 4E adds a guarded, offline-only session controller around the verified
Phase 4D shadow parity runner. It permits repeated comparison cycles while
writing only a dedicated parity-evidence journal outside the strategy
namespace.

It does not write or modify:

- namespaced strategy `state.json`
- namespaced strategy `ledger.csv`
- legacy Module 131 state, ledger, summary, report, or reason log
- canonical product paper runtime lifecycle
- product UI
- licensing or Machine ID

## Session gates

A session can start only when:

- recovery evidence is `READY_FLAT`;
- migration evidence is complete;
- selection remains `DISABLED`;
- runtime connection and runtime cutover are false;
- the parity journal is new and outside the strategy namespace.

A parity mismatch is journaled and immediately moves the session to `HALTED`.
No later evaluation cycle is accepted.

## Append-only evidence journal

The JSONL journal contains:

- `SESSION_STARTED`
- one `PARITY_MATCH` or `PARITY_MISMATCH` record per unique cycle ID
- `SESSION_CLOSED`

Every record has:

- contiguous sequence number
- previous-record SHA-256
- deterministic record SHA-256
- session, selection, and recovery identity
- input identity and parity-result hash
- zero runtime/state/ledger write flags

The journal rejects tampering, broken hash chains, duplicate cycle IDs,
multiple session IDs, records after closure, and concurrent writers.

## Safety boundary

Phase 4E is shadow evidence only. It does not enable strategy activation,
canonical lifecycle writes, broker connectivity, order placement, auto
trading, option selling, real money, or profitability claims.
