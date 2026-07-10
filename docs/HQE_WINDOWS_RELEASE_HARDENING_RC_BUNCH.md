# HQE Windows Release Hardening and RC Dry-Run Bunch

This cohesive roadmap bunch combines:

1. Windows release manifest
2. One-icon desktop shortcut installer and remover
3. Offline license lifecycle and expiry states
4. Machine-bound license integrity validation
5. Development-mode license handling
6. User strategy/settings backup ZIP
7. Path-safe restore staging with no automatic overwrite
8. Diagnostics JSON/ZIP bundle
9. Release-candidate guard dry run
10. Required-file, app-compile and component-guard checks
11. App-native Windows Release Center

Restore policy:

Backups are extracted only into a restore-staging folder. Existing live
workspace files are never overwritten automatically.

License note:

Production offline verification uses an environment-provided HMAC-SHA256
verification key. The verification key is not stored in the repository.
Git development workspaces remain in DEVELOPMENT_MODE.

Release-candidate dry run:

The dry run performs only file, compile, license and guard checks. It does
not fetch market data, start paper watch, run a backtest, generate reports,
connect broker execution or place orders.

Permanent safety:

- Paper/data/research only: YES
- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO
- Option selling: NO

This is not a profitability claim.
