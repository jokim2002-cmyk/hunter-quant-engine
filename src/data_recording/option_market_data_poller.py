"""Broker-agnostic option market data poller."""

from __future__ import annotations

from collections.abc import Sequence

from src.data_recording.option_market_data_poll_result import (
    OptionMarketDataPollResult,
)
from src.data_recording.option_market_data_source import OptionMarketDataSource


class OptionMarketDataPoller:
    """Poll option market data from a broker-agnostic source."""

    def __init__(self, data_source: OptionMarketDataSource) -> None:
        self._data_source = data_source

    def poll_snapshot(self) -> OptionMarketDataPollResult:
        """Poll the latest option chain snapshot."""
        return OptionMarketDataPollResult(snapshot=self._data_source.get_option_chain_snapshot())

    def poll_premium_candles(
        self,
        symbols: Sequence[str],
    ) -> OptionMarketDataPollResult:
        """Poll premium candles for one or more symbols."""
        if not symbols:
            raise ValueError("option premium candle symbols are required")

        return OptionMarketDataPollResult(
            premium_candles_by_symbol=self._data_source.get_option_premium_candles(
                symbols
            )
        )

    def poll(
        self,
        premium_symbols: Sequence[str] = (),
        include_snapshot: bool = True,
    ) -> OptionMarketDataPollResult:
        """Poll snapshot and premium candles together."""
        if not include_snapshot and not premium_symbols:
            return OptionMarketDataPollResult()

        snapshot = (
            self._data_source.get_option_chain_snapshot() if include_snapshot else None
        )
        premium_candles_by_symbol = {}
        if premium_symbols:
            premium_candles_by_symbol = self._data_source.get_option_premium_candles(
                premium_symbols
            )

        return OptionMarketDataPollResult(
            snapshot=snapshot,
            premium_candles_by_symbol=premium_candles_by_symbol,
        )
