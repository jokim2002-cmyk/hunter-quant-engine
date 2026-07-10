# HQE Fyers Candle CSV Writer V1

This module converts the redacted FYERS history response into a deterministic CSV.

Mapping: epoch, open, high, low, close, volume, source.

Controls include IST datetime conversion, duplicate removal, chronological sorting, atomic replacement, returned/written row verification, and protection against overwriting on API errors.

Safety remains paper/data only. No order or broker-execution APIs are used.

This is not a profitability claim.
