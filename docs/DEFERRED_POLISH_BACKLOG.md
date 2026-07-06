# HQE Deferred Polish Backlog

This backlog exists to prevent micro-polish from blocking the Paper MVP v0.1
release.

## Rule

Do not work on these items one by one before Paper MVP v0.1 is closed.

Polish must be bundled into a dedicated polish module after the end-to-end paper
trading workflow runs successfully.

## Deferred Polish Items

- Improve terminal formatting for long JSON paths.
- Add richer report layout.
- Add optional CSV/table summaries.
- Improve shortcut wording.
- Consolidate repeated docs sections.
- Add dashboard or UI only after CLI workflow is stable.
- Add historical run comparison views.
- Add charts only after evidence runner output is stable.
- Add screenshots or examples only after the operator workflow is final.

## Not Deferred

These are not polish and may block v0.1:

- Broken tests.
- Broken paper workflow.
- Incorrect PnL labels.
- Missing safety labels.
- Any accidental broker/live-order path.
- Any missing evidence gate that could lead to unsafe live trading.

## Bundle Policy

When polish starts, it should be one planned module:

    Deferred polish bundle

That module should include related formatting/docs/UX improvements together,
with targeted tests and full-suite validation.
