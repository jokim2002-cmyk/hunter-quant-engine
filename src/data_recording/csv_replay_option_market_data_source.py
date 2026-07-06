"""Broker-agnostic CSV replay option market data source."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from src.backtesting.option_chain_snapshot_csv_loader import OptionChainSnapshotCsvLoader
from src.backtesting.option_premium_candle_csv_loader import OptionPremiumCandleCsvLoader
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_premium_candle import OptionPremiumCandle


class CsvReplayOptionMarketDataSource:
    """Replay previously recorded option market data from CSV files.

    Implements the OptionMarketDataSource protocol shape.
    Broker-agnostic. No broker or API code. Does not place orders.
    Not a profitability claim.
    """

    def __init__(
        self,
        snapshot_csv_path: str | Path | None = None,
        premium_csv_path: str | Path | None = None,
    ) -> None:
        self._snapshot_csv_path = Path(snapshot_csv_path) if snapshot_csv_path else None
        self._premium_csv_path = Path(premium_csv_path) if premium_csv_path else None
        self._snapshots: tuple[OptionChainSnapshot, ...] | None = None
        self._premium_candles: dict[str, tuple[OptionPremiumCandle, ...]] | None = None

    def _load_snapshots(self) -> tuple[OptionChainSnapshot, ...]:
        if self._snapshots is None:
            if self._snapshot_csv_path is None:
                raise ValueError("snapshot_csv_path is required to replay snapshots")
            self._snapshots = OptionChainSnapshotCsvLoader().load_snapshots(
                self._snapshot_csv_path
            )
        return self._snapshots

    def _load_premium_candles(self) -> dict[str, tuple[OptionPremiumCandle, ...]]:
        if self._premium_candles is None:
            if self._premium_csv_path is None:
                raise ValueError("premium_csv_path is required to replay premium candles")
            self._premium_candles = OptionPremiumCandleCsvLoader().load_grouped_candles(
                self._premium_csv_path
            )
        return self._premium_candles

    def get_option_chain_snapshot(self) -> OptionChainSnapshot:
        """Return the first loaded snapshot (earliest by timestamp)."""
        snapshots = self._load_snapshots()
        return snapshots[0]

    def get_option_premium_candles(
        self,
        symbols: Sequence[str],
    ) -> Mapping[str, Sequence[OptionPremiumCandle]]:
        """Return premium candles for the requested symbols."""
        if not symbols:
            raise ValueError("option premium candle symbols are required")

        candles_by_symbol = self._load_premium_candles()
        result: dict[str, tuple[OptionPremiumCandle, ...]] = {}
        for symbol in symbols:
            if not symbol.strip():
                raise ValueError("option premium candle symbol is required")
            if symbol not in candles_by_symbol:
                raise ValueError(
                    f"option premium candles not found for symbol: {symbol}"
                )
            result[symbol] = candles_by_symbol[symbol]
        return result
