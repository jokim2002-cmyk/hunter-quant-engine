# HQE Multi-Strategy Phase 7 — Parallel Isolated Paper Observation

## Purpose

Phase 7 adds a deterministic observation-only fan-out for two or more reviewed
forward-compatible strategy configurations. The same normalized recorded-paper
input is evaluated for every lane, while each lane keeps its own state, ledger,
event chain, summary and paper P&L.

This is comparison evidence only. It does not rank strategies, claim
profitability, select a paper strategy, create a human gate, connect to the
canonical paper runtime or place an order.

## Observation namespace

Every session is stored only under:

```text
<workspace>/HQE_MULTI_STRATEGY_PARALLEL_OBSERVATION/
  sessions/<session_id>/
    SESSION_MANIFEST.json
    SESSION_SUMMARY.json
    SESSION_EVENTS.jsonl
    lanes/<strategy>.<version>.<parameters_hash>/
      OBSERVATION_STATE.json
      OBSERVATION_LEDGER.csv
      OBSERVATION_SUMMARY.json
      OBSERVATION_EVENTS.jsonl
```

No file is written into `HQE_PAPER_PRODUCT_RUNTIME`, a canonical Module 131
strategy namespace, the active-selection file, the Phase 4 human gate or the
Phase 6 installed-metadata catalog.

## Eligibility

A lane is accepted only when all checks pass:

- the strategy and version exist in the deterministic local registry
- the implementation status is `EXECUTABLE_REVIEWED`
- the implementation satisfies the reviewed recorded/forward-paper adapter
- manifest parameters validate and are normalized
- the required timeframe matches the session
- its lane identity is unique after parameter normalization

Metadata-only imported packages and reviewed implementations without the
recorded-paper adapter remain visible as ineligible and cannot enter a session.

## Session lifecycle

1. Create an isolated session with at least two lanes.
2. Fan one normalized recorded input into every lane.
3. Evaluate every lane before writing cycle evidence.
4. Atomically rewrite each lane state and ledger file.
5. Append tamper-evident per-lane and session event chains.
6. Resume from verified files after restart.
7. Close the session only when all lanes are FLAT.

A duplicate cycle ID is rejected. State, event and ledger tampering is detected
before further observation or reporting.

## Paper lifecycle and P&L

Each lane has an independent option-buy paper lifecycle:

- eligible LONG/SHORT decision while FLAT opens its lane only
- mark price is observed independently for every lane
- target, stop-loss or opposite signal can close that lane
- realized and unrealized P&L are calculated only inside that lane
- session totals are evidence summaries, not ranking or profitability claims

One lane cannot overwrite another lane's state, ledger or P&L.

## Product UI

The Product Strategy Manager now includes a **Parallel Observation Center**.
The operator can:

- see reviewed forward-compatible lane eligibility
- create a 2+ lane isolated session
- choose recorded index and premium CSV inputs
- run a deterministic observation cycle
- inspect per-lane lifecycle and P&L evidence
- close a session only after every lane is FLAT
- open the isolated evidence directory

The center does not expose selection, canonical activation, cutover, runtime
start/stop, lifecycle-write or broker-order controls.

## Permanent safety boundary

```text
Paper-only observation                 YES
Per-lane state/ledger/P&L isolation    YES
Tamper-evident restart recovery        YES
Metadata-only imported strategy run    NO
Package source import/registration     NO
Paper strategy selection change        NO
Canonical runtime connection           NO
Human cutover gate creation             NO
Canonical state or ledger writes        NO
Broker execution / real orders          NO
Auto trading / real money               NO
Option selling                          NO
Profitability or winner claim           NO
```

## Next phase

Phase 8 performs final validation, visual acceptance, release/freeze refresh and
release closure. Phase 7 does not refresh the existing freeze manifest and does
not merge the feature branch into protected master.
