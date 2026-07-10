# HQE Final Paper-Only RC Evidence and Sign-Off

This final evidence bunch does not add product or trading features.

It:

1. Locates the latest operator-acceptance report
2. Rejects blocked acceptance
3. Rejects any enabled execution safety flag
4. Preserves the exact acceptance decision
5. Creates the paper-only RC sign-off manifest
6. Refreshes the Windows release manifest
7. Refreshes and verifies the SHA-256 freeze manifest
8. Records the final release-candidate status in HQE current status

Possible sign-off statuses:

- `PAPER_ONLY_RC_SIGNED_OFF`
- `PAPER_ONLY_RC_CONDITIONALLY_SIGNED_OFF`

Conditional sign-off means the product shell and permanent safety controls
passed, while one or more current data, license, workspace or validation
items still require operator review.

This sign-off applies only to the paper/data/research release candidate.

Real money, real orders, broker execution, auto trading and option selling
remain excluded.

This is not a profitability claim.
