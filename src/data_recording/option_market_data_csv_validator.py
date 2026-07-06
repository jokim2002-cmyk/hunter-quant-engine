"""Broker-agnostic validator for recorded option market data CSV files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.backtesting.option_chain_snapshot_csv_loader import OptionChainSnapshotCsvLoader
from src.backtesting.option_premium_candle_csv_loader import OptionPremiumCandleCsvLoader


@dataclass
class OptionMarketDataCsvValidationResult:
    """Result of validating recorded option market data CSV files.

    Broker-agnostic. Does not place orders. Not a profitability claim.
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    snapshot_count: int = 0
    premium_candle_count: int = 0
    symbols: list[str] = field(default_factory=list)


def validate_option_market_data_csvs(
    snapshot_csv_path: Path,
    premium_csv_path: Path,
) -> OptionMarketDataCsvValidationResult:
    """Validate recorded option market data CSV files before replay/backtest usage.

    Broker-agnostic offline check. Does not use any broker SDK.
    Does not use live or real market data. Does not place orders.
    Not a profitability claim.

    Returns OptionMarketDataCsvValidationResult with errors instead of raising
    for normal validation failures.
    """
    errors: list[str] = []
    snapshot_count = 0
    premium_candle_count = 0
    symbols: list[str] = []

    if not Path(snapshot_csv_path).exists():
        errors.append(f"snapshot CSV file not found: {snapshot_csv_path}")

    if not Path(premium_csv_path).exists():
        errors.append(f"premium CSV file not found: {premium_csv_path}")

    if errors:
        return OptionMarketDataCsvValidationResult(is_valid=False, errors=errors)

    try:
        snapshots = OptionChainSnapshotCsvLoader().load_snapshots(snapshot_csv_path)
        snapshot_count = len(snapshots)
        if snapshot_count == 0:
            errors.append("snapshot CSV loaded no snapshots")
    except Exception as exc:
        errors.append(f"snapshot CSV could not be loaded: {exc}")

    try:
        grouped = OptionPremiumCandleCsvLoader().load_grouped_candles(premium_csv_path)
        symbols = sorted(grouped.keys())
        premium_candle_count = sum(len(candles) for candles in grouped.values())
        if premium_candle_count == 0:
            errors.append("premium CSV loaded no candles")
    except Exception as exc:
        errors.append(f"premium CSV could not be loaded: {exc}")

    return OptionMarketDataCsvValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        snapshot_count=snapshot_count,
        premium_candle_count=premium_candle_count,
        symbols=symbols,
    )
