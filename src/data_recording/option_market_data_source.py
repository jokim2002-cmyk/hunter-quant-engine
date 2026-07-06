"""Protocol for broker-agnostic option market data sources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_premium_candle import OptionPremiumCandle


class OptionMarketDataSource(Protocol):
    """Interface for retrieving broker-agnostic option market data."""

    def get_option_chain_snapshot(self) -> OptionChainSnapshot:
        """Return the latest option chain snapshot."""

    def get_option_premium_candles(
        self,
        symbols: Sequence[str],
    ) -> Mapping[str, Sequence[OptionPremiumCandle]]:
        """Return premium candles grouped by symbol."""
