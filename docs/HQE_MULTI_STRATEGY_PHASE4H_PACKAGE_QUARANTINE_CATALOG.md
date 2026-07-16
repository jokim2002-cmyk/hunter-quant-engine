# HQE Multi-Strategy Phase 4H — Offline Package Quarantine and Read-Only Catalog

## Scope

Phase 4H adds a strictly offline, data-only strategy package quarantine and
import-preview surface.

It does not register, install, select, activate, execute, or connect any
quarantined strategy.

## Package boundary

Accepted packages must already satisfy the Phase 1 data-only package policy:

- `manifest.json`
- `checksums.json`
- optional Markdown, text, JSON, or CSV documentation/examples
- no Python, PowerShell, DLL, executable, shell, or binary implementation
- no symlinks
- exact checksum coverage
- canonical LONG/SHORT/NEUTRAL mapping
- paper-only safety flags

## Quarantine behavior

The source package is observed before and after copy. Every file is recorded
with path, size, timestamp, and SHA-256. A source mutation causes a fail-closed
stop.

The package is copied through a staging directory and atomically promoted to:

```text
<quarantine-root>/packages/
  <strategy-id>/<strategy-version>/<package-fingerprint>/
    package/
    preview.json
    quarantine.json
```

Existing matching quarantine records can be reused only after complete
fingerprint and file-hash verification. Existing inconsistent records are
rejected.

## Import preview

A preview can classify a package as:

- `PREVIEW_REVIEWED_REFERENCE`
- `PREVIEW_METADATA_ONLY`
- `DUPLICATE_EXISTING`
- `BLOCKED_ID_VERSION_CONFLICT`

All classifications remain non-authorizing:

- import disabled
- registry mutation disabled
- activation disabled
- runtime connection/cutover disabled
- state/ledger writes disabled
- broker execution disabled
- real money disabled

## Read-only catalog

The catalog combines built-in registrations and quarantined package previews.
It is deterministic, hashable, and display-only. All controls are disabled.

## Protected boundaries

This phase does not modify:

- `scripts/hqe_product_app_v2.py`
- `scripts/hqe_paper_product_runtime.py`
- `scripts/run_forward_intraday_paper_supervisor.py`
- `scripts/hqe_smc_live_direction.py`
- Module 131 state, ledger, reports, or recovery data
- licensing or Machine ID
- backtest engine/pipeline

## Next core path

Reviewed package approval workflow and atomic metadata-only catalog installation
in an isolated store, while activation and canonical lifecycle integration
remain disabled.
