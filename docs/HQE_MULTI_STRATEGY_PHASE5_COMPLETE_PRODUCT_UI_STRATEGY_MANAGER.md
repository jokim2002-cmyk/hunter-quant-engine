# HQE Multi-Strategy Phase 5 — Complete Product UI Strategy Manager

Phase 5 adds one product-facing strategy manager without creating another
runtime activation path.

The manager displays:

- available valid and invalid strategy packs
- selected paper configuration
- strategy ID, version, source, category and parameters
- validation and paper-only safety status
- Phase 4 canonical strategy identity, runtime mode and gate state
- current lifecycle and runtime-running truth
- exact blockers for selection changes

The manager can call the existing paper-configuration select/clear functions
only after the Phase 5 model confirms that the runtime is stopped and the
position lifecycle is not OPEN or HELD.

The manager cannot:

- create the Phase 4 human cutover gate
- activate or switch the canonical runtime
- start or stop Paper Trading
- write lifecycle/state/ledger evidence
- place real orders or invoke broker execution
- enable real money or option selling

Canonical activation remains a separate explicit human-gated operation.
