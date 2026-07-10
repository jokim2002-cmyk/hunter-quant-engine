# HQE Operator Acceptance Dry-Run and RC Sign-Off Bunch

This post-freeze acceptance bunch does not add trading features.

It combines:

1. One-icon launcher acceptance
2. Workspace write-permission acceptance
3. App navigation and no-execution checks
4. Read-only snapshots of all major product centers
5. Cross-center safety-flag verification
6. Final operator-journey decision
7. JSON and HTML acceptance reports
8. App-native Operator Acceptance & RC Sign-Off Center
9. Release manifest and SHA-256 freeze refresh

Acceptance decisions:

- `ACCEPTED_FOR_PAPER_ONLY_RC`
- `ACCEPTED_WITH_REVIEW`
- `BLOCKED`

`ACCEPTED_WITH_REVIEW` means the product shell and safety controls pass,
while current data, validation, license or workspace evidence still needs
operator review.

The dry run never starts paper watch, fetches data, runs backtests, creates
reports, changes backups, connects broker execution or places orders.

This is not a profitability claim.
