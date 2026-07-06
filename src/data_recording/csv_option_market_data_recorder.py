"""CSV-based option market data recorder."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from src.backtesting.option_chain_snapshot_csv_writer import (
    OptionChainSnapshotCsvWriter,
)
from src.backtesting.option_premium_candle_csv_writer import (
    OptionPremiumCandleCsvWriter,
)
from src.data_recording.option_market_data_recording_result import (
    OptionMarketDataRecordingResult,
)
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_premium_candle import OptionPremiumCandle


class CsvOptionMarketDataRecorder:
    """Record option chain snapshots and premium candles to CSV files."""

    def __init__(
        self,
        snapshot_csv_path: str | Path,
        premium_csv_path: str | Path,
        snapshot_writer: OptionChainSnapshotCsvWriter | None = None,
        premium_writer: OptionPremiumCandleCsvWriter | None = None,
    ) -> None:
        self.snapshot_csv_path = Path(snapshot_csv_path)
        self.premium_csv_path = Path(premium_csv_path)
        self.snapshot_writer = snapshot_writer or OptionChainSnapshotCsvWriter()
        self.premium_writer = premium_writer or OptionPremiumCandleCsvWriter()

    def record_snapshot(
        self,
        snapshot: OptionChainSnapshot,
        snapshot_id: str | None = None,
    ) -> OptionMarketDataRecordingResult:
        """Append one snapshot to the snapshot CSV file."""
        self.snapshot_writer.append_snapshot(
            snapshot=snapshot,
            csv_path=self.snapshot_csv_path,
            snapshot_id=snapshot_id,
        )
        return OptionMarketDataRecordingResult(
            snapshots_recorded=1,
            snapshot_output_path=str(self.snapshot_csv_path),
        )

    def record_premium_candles(
        self,
        symbol: str,
        candles: Sequence[OptionPremiumCandle],
    ) -> OptionMarketDataRecordingResult:
        """Append premium candles for one symbol to the premium CSV file."""
        self.premium_writer.append_candles(
            symbol=symbol,
            candles=candles,
            csv_path=self.premium_csv_path,
        )
        return OptionMarketDataRecordingResult(
            premium_symbols_recorded=1,
            premium_candles_recorded=len(candles),
            premium_output_path=str(self.premium_csv_path),
        )

    def record_batch(
        self,
        snapshots: Sequence[OptionChainSnapshot] = (),
        premium_candles_by_symbol: Mapping[str, Sequence[OptionPremiumCandle]] | None = None,
    ) -> OptionMarketDataRecordingResult:
        """Record snapshots and premium candles for a whole batch."""
        if premium_candles_by_symbol is None:
            premium_candles_by_symbol = {}

        snapshot_count = 0
        for snapshot in snapshots:
            self.record_snapshot(snapshot)
            snapshot_count += 1

        premium_symbol_count = 0
        premium_candles_count = 0
        for symbol, candles in premium_candles_by_symbol.items():
            self.record_premium_candles(symbol, candles)
            premium_symbol_count += 1
            premium_candles_count += len(candles)

        return OptionMarketDataRecordingResult(
            snapshots_recorded=snapshot_count,
            premium_symbols_recorded=premium_symbol_count,
            premium_candles_recorded=premium_candles_count,
            snapshot_output_path=str(self.snapshot_csv_path),
            premium_output_path=str(self.premium_csv_path),
        )
