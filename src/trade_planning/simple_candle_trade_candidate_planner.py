"""
Simple Candle Trade Candidate Planner

Creates basic trade candidates from the current candle.
"""

from src.strategy.signal_type import SignalType
from src.strategy.strategy_context import StrategyContext
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.base_trade_candidate_planner import (
    BaseTradeCandidatePlanner,
)
from src.trade_planning.trade_candidate import TradeCandidate


class SimpleCandleTradeCandidatePlanner(BaseTradeCandidatePlanner):
    """
    Creates trade candidates using the latest candle.

    LONG:
        entry_price = latest candle close
        stop_loss = latest candle low

    SHORT:
        entry_price = latest candle close
        stop_loss = latest candle high

    NEUTRAL:
        no trade candidate
    """

    def plan(
        self,
        signal: TradeSignal,
        context: StrategyContext,
    ) -> tuple[TradeCandidate, ...]:
        """
        Create trade candidates from the latest candle.

        Args:
            signal: Immutable strategy signal.
            context: Immutable strategy context.

        Returns:
            Tuple containing one TradeCandidate for directional signals.
            Empty tuple for neutral signals or missing candle data.
        """
        if signal.signal_type == SignalType.NEUTRAL:
            return ()

        if not context.candles:
            return ()

        latest_candle = context.candles[-1]

        if signal.signal_type == SignalType.LONG:
            return (
                TradeCandidate(
                    signal=signal,
                    entry_price=latest_candle.close,
                    stop_loss=latest_candle.low,
                ),
            )

        if signal.signal_type == SignalType.SHORT:
            return (
                TradeCandidate(
                    signal=signal,
                    entry_price=latest_candle.close,
                    stop_loss=latest_candle.high,
                ),
            )

        raise ValueError("Unsupported trade signal type.")
