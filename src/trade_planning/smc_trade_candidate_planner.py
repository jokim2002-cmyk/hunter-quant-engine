"""
SMC Trade Candidate Planner

Creates institutional trade candidates from SMC entry zones.
"""

from src.models.fair_value_gap import FairValueGap
from src.models.order_block import OrderBlock
from src.strategy.signal_type import SignalType
from src.strategy.strategy_context import StrategyContext
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.base_trade_candidate_planner import (
    BaseTradeCandidatePlanner,
)
from src.trade_planning.trade_candidate import TradeCandidate

EntryZone = FairValueGap | OrderBlock


class SMCTradeCandidatePlanner(BaseTradeCandidatePlanner):
    """
    Creates trade candidates from Smart Money Concept entry zones.

    LONG:
        Entry = bullish order block midpoint, falling back to bullish FVG midpoint.
        Stop loss = selected zone low.

    SHORT:
        Entry = bearish order block midpoint, falling back to bearish FVG midpoint.
        Stop loss = selected zone high.

    NEUTRAL:
        No trade candidate.
    """

    def plan(
        self,
        signal: TradeSignal,
        context: StrategyContext,
    ) -> tuple[TradeCandidate, ...]:
        """
        Create SMC trade candidates from institutional entry zones.

        Args:
            signal: Immutable strategy signal.
            context: Immutable strategy context.

        Returns:
            Tuple containing one TradeCandidate when a matching SMC entry
            zone exists. Empty tuple for neutral signals or missing entry zones.
        """
        if signal.signal_type == SignalType.NEUTRAL:
            return ()

        if signal.signal_type == SignalType.LONG:
            return self._plan_long(
                signal=signal,
                context=context,
            )

        if signal.signal_type == SignalType.SHORT:
            return self._plan_short(
                signal=signal,
                context=context,
            )

        raise ValueError("Unsupported trade signal type.")

    def _plan_long(
        self,
        signal: TradeSignal,
        context: StrategyContext,
    ) -> tuple[TradeCandidate, ...]:
        entry_zone = self._select_bullish_entry_zone(context)

        if entry_zone is None:
            return ()

        return (
            TradeCandidate(
                signal=signal,
                entry_price=self._midpoint(entry_zone),
                stop_loss=entry_zone.low,
            ),
        )

    def _plan_short(
        self,
        signal: TradeSignal,
        context: StrategyContext,
    ) -> tuple[TradeCandidate, ...]:
        entry_zone = self._select_bearish_entry_zone(context)

        if entry_zone is None:
            return ()

        return (
            TradeCandidate(
                signal=signal,
                entry_price=self._midpoint(entry_zone),
                stop_loss=entry_zone.high,
            ),
        )

    def _select_bullish_entry_zone(
        self,
        context: StrategyContext,
    ) -> EntryZone | None:
        bullish_order_block = self._first_bullish_order_block(context)

        if bullish_order_block is not None:
            return bullish_order_block

        return self._first_bullish_fair_value_gap(context)

    def _select_bearish_entry_zone(
        self,
        context: StrategyContext,
    ) -> EntryZone | None:
        bearish_order_block = self._first_bearish_order_block(context)

        if bearish_order_block is not None:
            return bearish_order_block

        return self._first_bearish_fair_value_gap(context)

    def _first_bullish_order_block(
        self,
        context: StrategyContext,
    ) -> OrderBlock | None:
        for order_block in context.order_blocks:
            if order_block.is_bullish():
                return order_block

        return None

    def _first_bearish_order_block(
        self,
        context: StrategyContext,
    ) -> OrderBlock | None:
        for order_block in context.order_blocks:
            if order_block.is_bearish():
                return order_block

        return None

    def _first_bullish_fair_value_gap(
        self,
        context: StrategyContext,
    ) -> FairValueGap | None:
        for fair_value_gap in context.fair_value_gaps:
            if fair_value_gap.is_bullish():
                return fair_value_gap

        return None

    def _first_bearish_fair_value_gap(
        self,
        context: StrategyContext,
    ) -> FairValueGap | None:
        for fair_value_gap in context.fair_value_gaps:
            if fair_value_gap.is_bearish():
                return fair_value_gap

        return None

    def _midpoint(
        self,
        entry_zone: EntryZone,
    ) -> float:
        return (entry_zone.high + entry_zone.low) / 2.0
