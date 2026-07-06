"""Protocol for broker-agnostic option market data recorders."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_premium_candle import OptionPremiumCandle
from src.data_recording.option_market_data_recording_result import (
    OptionMarketDataRecordingResult,
)


class OptionMarketDataRecorder(Protocol):
    """Interface for recording market data to a broker-agnostic store."""

    def record_snapshot(
        self,
        snapshot: OptionChainSnapshot,
        snapshot_id: str | None = None,
    ) -> OptionMarketDataRecordingResult:
        """Record a single option chain snapshot."""

    def record_premium_candles(
        self,
        symbol: str,
        candles: Sequence[OptionPremiumCandle],
    ) -> OptionMarketDataRecordingResult:
        """Record premium candles for one symbol."""

    def record_batch(
        self,
        snapshots: Sequence[OptionChainSnapshot] = (),
        premium_candles_by_symbol: Mapping[str, Sequence[OptionPremiumCandle]] | None = None,
    ) -> OptionMarketDataRecordingResult:
        """Record snapshots and premium candles in one batch."""
