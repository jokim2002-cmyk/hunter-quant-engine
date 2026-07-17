# HQE Multi-Strategy Phase 8 — Final Validation and Release Closure

Phase 8 closes the multi-strategy roadmap as a paper/data/research release
candidate. It does not merge the feature branch into protected master and does
not activate a strategy.

## Closure sequence

1. Verify the protected master and Phase 7 checkpoint baseline.
2. Install the release-closure scripts, manifests, tests and documentation.
3. Run actual Windows Tk GUI render smoke for Advanced Tools and all zero-arg
   product centers in an isolated workspace.
4. Refresh the SHA-256 release freeze from the current RC5 required-file list.
5. Close the four previously deferred release/freeze tests.
6. Run focused release tests, cumulative multi-strategy regression,
   environment recovery and the full functional suite.
7. Write final Phase 8 closure evidence, refresh the freeze again and re-run
   final release gates against the final bytes.
8. Commit and push the exact Phase 8 scope only after every gate passes.

## Visual acceptance truth

The workflow performs actual automated Windows GUI render smoke. It does not
capture screenshots and does not claim a manual human visual sign-off. The
report records both facts explicitly.

## Permanent safety boundary

Phase 8 cannot select or activate a strategy, create the Phase 4 human cutover
gate, control the canonical runtime, write canonical lifecycle evidence or
place real orders. Real money, broker execution, auto trading and option
selling remain disabled.

The protected master remains unchanged. A later master merge requires separate
review and explicit approval outside this Phase 8 closure.

## Visible multi-strategy navigation maintenance

Post-closure operator review found that Product Strategy Manager was reachable
only through the secondary Advanced Tools Hub. The main Advanced Tools page now
provides direct visible buttons for Product Strategy Manager and Parallel
Observation Center. Automated acceptance invokes both real buttons and verifies
the resulting dialogs, so hidden callback discovery alone cannot pass the gate.

The repair remains paper/data/research only. It does not select or activate a
strategy, create a cutover gate, control the canonical runtime, write canonical
state/ledger evidence, or enable real execution.
