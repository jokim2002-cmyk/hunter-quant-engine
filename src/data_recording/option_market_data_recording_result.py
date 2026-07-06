"""Immutable result object for market data recording operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OptionMarketDataRecordingResult:
    """Represents the outcome of recording market data to CSV files."""

    snapshots_recorded: int = 0
    premium_symbols_recorded: int = 0
    premium_candles_recorded: int = 0
    snapshot_output_path: str | None = None
    premium_output_path: str | None = None

    def __post_init__(self) -> None:
        """Validate non-negative counts."""
        for field_name in (
            "snapshots_recorded",
            "premium_symbols_recorded",
            "premium_candles_recorded",
        ):
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"{field_name} must be greater than or equal to 0")

    @property
    def has_recorded_data(self) -> bool:
        """Return True when any market data was recorded."""
        return self.snapshots_recorded > 0 or self.premium_candles_recorded > 0
