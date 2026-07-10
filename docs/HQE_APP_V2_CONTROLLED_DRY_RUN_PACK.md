# HQE App V2 Controlled Dry Run Pack

This pack performs two bounded paper-watch runs against the active forward-validation workspace.

Each run:

1. starts the persistent paper-watch loop,
2. observes the process for a fixed duration,
3. captures stdout and stderr,
4. records workspace file changes,
5. terminates the full process tree,
6. writes a structured result.

The final decision is `APP_V2_CONTROLLED_DRY_RUNS_COMPLETE` only when preflight and both runs pass.

Safety remains fixed:

- paper only,
- data only,
- no real money,
- no real orders,
- no broker execution,
- no auto trading.

This is not a profitability claim.
