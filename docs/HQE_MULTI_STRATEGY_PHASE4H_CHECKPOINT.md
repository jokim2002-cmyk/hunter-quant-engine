# HQE Multi-Strategy Checkpoint — Phase 4H

## Protected baseline

- Protected master baseline: `c5704aa`
- Development branch: `feature/hqe-multi-strategy-phase1`
- Product mode: PAPER / DATA / RESEARCH ONLY
- Real orders, broker execution, auto trading and real money: DISABLED
- Canonical product runtime and licensing behavior: UNCHANGED

## Roadmap progress

Completed:

- Phase 0 — read-only architecture audit
- Phase 1 — strategy contract and registry foundation
- Phase 2 — current strategy compatibility adapter
- Phase 3 — registered backtest and normalized recorded-evaluation integration

Phase 4 preparation completed through checkpoint 4H:

- disabled strategy selection snapshot
- namespaced state, ledger and recovery foundation
- read-only legacy migration planner
- isolated flat-state copy dry run
- offline recovery and direct/registered parity
- guarded shadow sessions and append-only evidence journal
- read-only runtime observations and operator evidence view
- disabled activation preflight and read-only UI model
- data-only package quarantine, import preview and read-only catalog

Phase 4 is not complete yet because the selected registered strategy has not
been connected to the canonical product paper lifecycle.

Pending:

- complete Phase 4 canonical one-active-strategy paper lifecycle integration
- Phase 5 actual Product UI strategy manager
- Phase 6 reviewed approval and atomic metadata-only installation workflow
- Phase 7 parallel isolated paper observation
- Phase 8 full regression, visual acceptance, freeze refresh and release closure

Honest overall roadmap estimate at this checkpoint: approximately 50–55%.

## Laptop handoff

The existing PC license key is machine-bound and must not be reused on the
laptop. Generate a new license for the laptop Machine ID using the same owner
signing key pair.

Owner key directory:

`D:\HQE_PRODUCT_LICENSE_OWNER`

Required files:

- `hqe_owner_private_key.json`
- `hqe_license_public_key.json`

Never commit these files to Git. Transfer them securely. Do not run
`--init-owner-keys` or `--force-new-keys`, because replacement owner keys would
break compatibility with licenses signed by the existing owner key pair.

## Next core path

Reviewed package approval workflow and atomic metadata-only catalog
installation, while activation and canonical lifecycle cutover remain disabled.
