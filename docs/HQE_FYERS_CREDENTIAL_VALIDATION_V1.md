# HQE Fyers Credential Validation V1

This module validates Fyers credential readiness without printing secret values.

It records presence, length, SHA-256 fingerprints, quote/whitespace/newline corruption, latest redacted authentication code, launcher environment alignment, and post-refresh one-shot revalidation readiness.

Authentication code `-16` is classified as `AUTH_FAILED_CODE_-16`.

Safety:

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO

Never paste access tokens into chat or commit them to Git.
