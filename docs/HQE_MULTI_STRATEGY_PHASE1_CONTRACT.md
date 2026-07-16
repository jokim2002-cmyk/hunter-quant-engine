# HQE Multi-Strategy Phase 1 Contract

## Scope

This phase adds a new, isolated contract and registry foundation only. It does
not connect to the product UI, canonical paper runtime, Module 131 state,
licensing, Machine ID, brokers, or real orders.

## Decisions

- Registration identity is `(strategy_id, strategy_version)`.
- Strategy outputs remain `LONG`, `SHORT`, and `NEUTRAL`.
- Option mapping remains `LONG -> CE_BUY`, `SHORT -> PE_BUY`,
  `NEUTRAL -> NO_TRADE`.
- All execution and money safety flags fail closed.
- Imported V1 packages are data-only and cannot contain executable code.
- `implementation_key` binds a manifest only to a reviewed local factory.
- The registry is in-memory in Phase 1 and performs no filesystem writes.
- A strategy without a reviewed factory is visible as `METADATA_ONLY` and
  cannot execute.
- No dynamic import is performed by the registry or package validator.

## Deferred

Current-strategy compatibility adapter, backtest routing, forward runtime,
state/ledger migration, UI selection, and parallel paper testing are separate
later phases.
