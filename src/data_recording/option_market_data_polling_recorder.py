"""Broker-agnostic poll-and-record service for option market data."""

from __future__ import annotations

from collections.abc import Sequence

from src.data_recording.csv_option_market_data_recorder import CsvOptionMarketDataRecorder
from src.data_recording.option_market_data_poller import OptionMarketDataPoller
from src.data_recording.option_market_data_recording_result import (
    OptionMarketDataRecordingResult,
)


class OptionMarketDataPollingRecorder:
    """Connect OptionMarketDataPoller with CsvOptionMarketDataRecorder."""

    def __init__(
        self,
        poller: OptionMarketDataPoller,
        recorder: CsvOptionMarketDataRecorder,
    ) -> None:
        self._poller = poller
        self._recorder = recorder

    def poll_and_record_snapshot(
        self,
        snapshot_id: str | None = None,
    ) -> OptionMarketDataRecordingResult:
        """Poll and record one option chain snapshot."""
        result = self._poller.poll_snapshot()
        if not result.has_snapshot:
            return OptionMarketDataRecordingResult()
        return self._recorder.record_snapshot(result.snapshot, snapshot_id=snapshot_id)

    def poll_and_record_premium_candles(
        self,
        symbols: Sequence[str],
    ) -> OptionMarketDataRecordingResult:
        """Poll and record premium candles for the given symbols."""
        result = self._poller.poll_premium_candles(symbols)
        if not result.has_premium_candles:
            return OptionMarketDataRecordingResult()
        return self._recorder.record_batch(
            premium_candles_by_symbol=result.premium_candles_by_symbol
        )

    def poll_and_record(
        self,
        premium_symbols: Sequence[str] = (),
        include_snapshot: bool = True,
        snapshot_id: str | None = None,
    ) -> OptionMarketDataRecordingResult:
        """Poll and record snapshot and/or premium candles together."""
        result = self._poller.poll(
            premium_symbols=premium_symbols,
            include_snapshot=include_snapshot,
        )
        if not result.has_data:
            return OptionMarketDataRecordingResult()

        snapshots_recorded = 0
        snapshot_output_path = None
        if result.has_snapshot:
            snap_result = self._recorder.record_snapshot(
                result.snapshot, snapshot_id=snapshot_id
            )
            snapshots_recorded = snap_result.snapshots_recorded
            snapshot_output_path = snap_result.snapshot_output_path

        premium_symbols_recorded = 0
        premium_candles_recorded = 0
        premium_output_path = None
        if result.has_premium_candles:
            prem_result = self._recorder.record_batch(
                premium_candles_by_symbol=result.premium_candles_by_symbol
            )
            premium_symbols_recorded = prem_result.premium_symbols_recorded
            premium_candles_recorded = prem_result.premium_candles_recorded
            premium_output_path = prem_result.premium_output_path

        return OptionMarketDataRecordingResult(
            snapshots_recorded=snapshots_recorded,
            premium_symbols_recorded=premium_symbols_recorded,
            premium_candles_recorded=premium_candles_recorded,
            snapshot_output_path=snapshot_output_path,
            premium_output_path=premium_output_path,
        )
