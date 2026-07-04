# Changelog

All notable changes to Hunter Quant Engine will be documented in this file.

This project follows an honest engineering rule:

- No fake profit claims
- Every feature must have tests
- Every strategy must be benchmarked after costs
- Heavy real-data runs are PC-only

---

## Unreleased

### Added

- Strategy config system for SMC strategy behavior.
- Strict, balanced, and relaxed strategy modes.
- CLI support for selecting strategy mode.
- Strategy mode benchmark runner.
- PC-only strategy mode benchmark shortcut.
- Strategy experiment dry-run runner.
- Experiment result ranking helpers.
- Best/worst experiment report sections.
- Sorted experiment summary CSV by net PnL.
- PC-only strategy experiment shortcut.
- PC benchmark and experiment runbook.
- README documentation for current HQE workflow.
- README documentation tests.

### Changed

- ROADMAP updated with strategy mode benchmark status.
- ROADMAP updated with experiment runner status.
- README updated from old backtesting-only status to current research workflow.
- Generated benchmark outputs ignored.
- Generated experiment outputs ignored.

### Fixed

- Strategy mode benchmark script can now run directly as a file.
- README architecture typos removed.

### Safety

- Full real-data strategy mode benchmark marked as PC-only.
- Full strategy experiment execution marked as PC-only.
- Laptop workflow restricted to code, tests, dry-runs, and Git operations.

### Current Test Count

- 618 tests passing.

---

## Earlier Foundation

### Added

- Clean Python architecture.
- Smart Money Concepts detection layer.
- Swing detection.
- Market structure detection.
- BOS and CHOCH detection.
- Liquidity point detection.
- Equal high and equal low detection.
- Liquidity cluster detection.
- Liquidity sweep detection.
- Fair Value Gap detection.
- Order Block detection.
- SMC strategy signal generation.
- Risk profile and trade planning.
- Backtest pipeline.
- Trade CSV export.
- Net equity curve export.
- Transaction cost modeling.
- Buy-and-hold benchmark comparison.
- FYERS NIFTY historical data workflow.
- FYERS token refresh helper.
- PC and laptop GitHub workflow shortcuts.

### Benchmark Truth

- First real FYERS NIFTY baseline underperformed buy-and-hold.
- This is treated as the first honest baseline, not a failure.
- Future strategy improvements must be judged after transaction costs.
