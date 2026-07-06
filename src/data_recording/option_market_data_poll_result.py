"""Immutable result object for option market data polling."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_premium_candle import OptionPremiumCandle


@dataclass(frozen=True)
class OptionMarketDataPollResult:
    """Represents the outcome of a market data poll."""

    snapshot: OptionChainSnapshot | None = None
    premium_candles_by_symbol: Mapping[str, tuple[OptionPremiumCandle, ...]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """Validate and normalize candle collections to tuples."""
        normalized: dict[str, tuple[OptionPremiumCandle, ...]] = {}
        for symbol, candles in self.premium_candles_by_symbol.items():
            if not symbol.strip():
                raise ValueError("option premium candle symbol is required")

            normalized_candles = tuple(candles)
            if not normalized_candles:
                raise ValueError(
                    f"option premium candles are required for symbol: {symbol}"
                )

            normalized[symbol] = normalized_candles

        object.__setattr__(self, "premium_candles_by_symbol", normalized)

    @property
    def has_snapshot(self) -> bool:
        """Return True when a snapshot is present."""
        return self.snapshot is not None

    @property
    def premium_symbols_count(self) -> int:
        """Return the number of premium candle symbols in the result."""
        return len(self.premium_candles_by_symbol)

    @property
    def premium_candles_count(self) -> int:
        """Return the total number of premium candles in the result."""
        return sum(len(candles) for candles in self.premium_candles_by_symbol.values())

    @property
    def has_premium_candles(self) -> bool:
        """Return True when any premium candles are present."""
        return self.premium_candles_count > 0

    @property
    def has_data(self) -> bool:
        """Return True when any market data was captured."""
        return self.has_snapshot or self.has_premium_candles
