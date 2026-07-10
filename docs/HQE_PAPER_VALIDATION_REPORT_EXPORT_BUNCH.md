# HQE Paper Validation Intelligence and Report Export Bunch

This cohesive roadmap bunch combines:

1. Forward-validation progress engine
2. Observed days, trades, valid trade-days and expiry-week tracking
3. No-trade reason extraction and classification
4. Locked-candidate strategy-drift detection
5. Weekly validation summaries
6. Safety and kill-switch decision priority
7. Formal validation decision status
8. Daily and weekly CSV exports
9. No-trade-reason CSV export
10. Customer-readable HTML report
11. Machine-readable JSON report
12. ZIP evidence pack
13. App-native Paper Validation Intelligence Center

Decision statuses:

- HOLD_MORE_DATA_REQUIRED
- READY_FOR_FORMAL_REVIEW
- DRIFT_REVIEW_REQUIRED
- SAFETY_REVIEW_REQUIRED
- KILL_SWITCH_TRIGGERED

READY_FOR_FORMAL_REVIEW means minimum evidence thresholds are complete.
It is not an approval for real trading and is not a profitability claim.

Permanent safety:

- Paper/data only: YES
- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO
- Option selling: NO
- Fake trades: NO
- Candidate tuning during validation: NO

This is not a profitability claim.
