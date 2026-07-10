# HQE App V2 Distribution and Clean Launch Flow

## Purpose

This pack creates a controlled App V2 release directory with:

- deterministic file manifest,
- SHA-256 fingerprints,
- preflight validation,
- clean user launcher,
- explicit paper-only safety locks.

## Launch sequence

1. Run preflight.
2. Confirm workspace, license, public key, Python environment, and required files.
3. Launch App V2 only after critical checks pass.
4. Keep real orders, broker execution, and auto trading locked.

## Distribution status

This is a source-based release readiness pack. It is not yet a standalone
compiled installer.

## Safety

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO

This is not a profitability claim.
