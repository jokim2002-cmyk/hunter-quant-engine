"""Broker-agnostic in-memory option market data source for tests and demos."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_premium_candle import OptionPremiumCandle


class InMemoryOptionMarketDataSource:
    """Fake broker-agnostic data source for tests and demos.

    Implements the OptionMarketDataSource protocol shape.
    No broker or API code.
    """

    def __init__(
        self,
        snapshot: OptionChainSnapshot | None = None,
        premium_candles_by_symbol: Mapping[str, Sequence[OptionPremiumCandle]] | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._premium_candles: dict[str, tuple[OptionPremiumCandle, ...]] = {}

        for symbol, candles in (premium_candles_by_symbol or {}).items():
            if not symbol.strip():
                raise ValueError("option premium candle symbol is required")
            normalized = tuple(candles)
            if not normalized:
                raise ValueError(
                    f"option premium candles are required for symbol: {symbol}"
                )
            self._premium_candles[symbol] = tuple(
                sorted(normalized, key=lambda c: c.timestamp)
            )

    @property
    def available_symbols(self) -> tuple[str, ...]:
        """Return all configured symbols sorted alphabetically."""
        return tuple(sorted(self._premium_candles))

    def get_option_chain_snapshot(self) -> OptionChainSnapshot:
        """Return the configured snapshot or raise if not available."""
        if self._snapshot is None:
            raise ValueError("option chain snapshot is not available")
        return self._snapshot

    def get_option_premium_candles(
        self,
        symbols: Sequence[str],
    ) -> Mapping[str, Sequence[OptionPremiumCandle]]:
        """Return premium candles for the requested symbols."""
        if not symbols:
            raise ValueError("option premium candle symbols are required")

        result: dict[str, tuple[OptionPremiumCandle, ...]] = {}
        for symbol in symbols:
            if not symbol.strip():
                raise ValueError("option premium candle symbol is required")
            if symbol not in self._premium_candles:
                raise ValueError(
                    f"option premium candles not found for symbol: {symbol}"
                )
            result[symbol] = self._premium_candles[symbol]

        return result
