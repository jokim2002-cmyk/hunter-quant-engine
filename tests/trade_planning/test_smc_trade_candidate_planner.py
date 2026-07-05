"""
SMC Trade Candidate Planner Tests
"""

from datetime import datetime

from src.strategy.signal_type import SignalType
from src.trade_planning.base_trade_candidate_planner import (
    BaseTradeCandidatePlanner,
)
from src.trade_planning.smc_trade_candidate_planner import (
    SMCTradeCandidatePlanner,
)
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.models.order_block_builder import OrderBlockBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder
from tests.builders.strategy.trade_signal_builder import TradeSignalBuilder


def test_smc_trade_candidate_planner_implements_base_contract():
    planner = SMCTradeCandidatePlanner()

    assert isinstance(planner, BaseTradeCandidatePlanner)


def test_plan_returns_empty_tuple_for_neutral_signal():
    signal = TradeSignalBuilder().neutral().build()
    order_block = OrderBlockBuilder().bullish().build()
    context = StrategyContextBuilder().with_order_blocks(order_block).build()

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates == ()


def test_plan_returns_empty_tuple_when_long_signal_has_no_bullish_entry_zone():
    signal = TradeSignalBuilder().long().build()
    bearish_order_block = OrderBlockBuilder().bearish().build()
    bearish_fvg = FairValueGapBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_order_blocks(bearish_order_block)
        .with_fair_value_gaps(bearish_fvg)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates == ()


def test_plan_returns_empty_tuple_when_short_signal_has_no_bearish_entry_zone():
    signal = TradeSignalBuilder().short().build()
    bullish_order_block = OrderBlockBuilder().bullish().build()
    bullish_fvg = FairValueGapBuilder().bullish().build()

    context = (
        StrategyContextBuilder()
        .with_order_blocks(bullish_order_block)
        .with_fair_value_gaps(bullish_fvg)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates == ()


def test_plan_creates_long_candidate_from_bullish_order_block():
    signal = TradeSignalBuilder().long().build()
    order_block = OrderBlockBuilder().bullish().build()
    context = StrategyContextBuilder().with_order_blocks(order_block).build()

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].signal is signal
    assert candidates[0].entry_price == (
        order_block.high + order_block.low
    ) / 2.0
    assert candidates[0].stop_loss == order_block.low


def test_plan_creates_short_candidate_from_bearish_order_block():
    signal = TradeSignalBuilder().short().build()
    order_block = OrderBlockBuilder().bearish().build()
    context = StrategyContextBuilder().with_order_blocks(order_block).build()

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].signal is signal
    assert candidates[0].entry_price == (
        order_block.high + order_block.low
    ) / 2.0
    assert candidates[0].stop_loss == order_block.high


def test_plan_creates_long_candidate_from_bullish_fvg_when_order_block_missing():
    signal = TradeSignalBuilder().long().build()
    fair_value_gap = FairValueGapBuilder().bullish().build()
    context = (
        StrategyContextBuilder()
        .with_fair_value_gaps(fair_value_gap)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].entry_price == (
        fair_value_gap.high + fair_value_gap.low
    ) / 2.0
    assert candidates[0].stop_loss == fair_value_gap.low


def test_plan_creates_short_candidate_from_bearish_fvg_when_order_block_missing():
    signal = TradeSignalBuilder().short().build()
    fair_value_gap = FairValueGapBuilder().bearish().build()
    context = (
        StrategyContextBuilder()
        .with_fair_value_gaps(fair_value_gap)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].entry_price == (
        fair_value_gap.high + fair_value_gap.low
    ) / 2.0
    assert candidates[0].stop_loss == fair_value_gap.high


def test_plan_prefers_order_block_over_fvg_for_long_signal():
    signal = TradeSignalBuilder().long().build()
    order_block = OrderBlockBuilder().bullish().build()
    fair_value_gap = FairValueGapBuilder().bullish().build()

    context = (
        StrategyContextBuilder()
        .with_order_blocks(order_block)
        .with_fair_value_gaps(fair_value_gap)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates[0].entry_price == (
        order_block.high + order_block.low
    ) / 2.0
    assert candidates[0].stop_loss == order_block.low


def test_plan_prefers_order_block_over_fvg_for_short_signal():
    signal = TradeSignalBuilder().short().build()
    order_block = OrderBlockBuilder().bearish().build()
    fair_value_gap = FairValueGapBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_order_blocks(order_block)
        .with_fair_value_gaps(fair_value_gap)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates[0].entry_price == (
        order_block.high + order_block.low
    ) / 2.0
    assert candidates[0].stop_loss == order_block.high


def test_plan_preserves_signal_type():
    signal = TradeSignalBuilder().short().build()
    order_block = OrderBlockBuilder().bearish().build()
    context = StrategyContextBuilder().with_order_blocks(order_block).build()

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert candidates[0].signal.signal_type is SignalType.SHORT

def test_plan_uses_latest_bullish_order_block_for_long_signal():
    signal = TradeSignalBuilder().long().build()
    older_order_block = (
        OrderBlockBuilder()
        .bullish()
        .with_high(110.0)
        .with_low(100.0)
        .created_at(datetime(2026, 1, 1, 9, 15))
        .build()
    )
    latest_order_block = (
        OrderBlockBuilder()
        .bullish()
        .with_high(130.0)
        .with_low(120.0)
        .created_at(datetime(2026, 1, 1, 9, 30))
        .build()
    )
    context = (
        StrategyContextBuilder()
        .with_order_blocks(older_order_block, latest_order_block)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].entry_price == 125.0
    assert candidates[0].stop_loss == 120.0


def test_plan_uses_latest_bearish_order_block_for_short_signal():
    signal = TradeSignalBuilder().short().build()
    older_order_block = (
        OrderBlockBuilder()
        .bearish()
        .with_high(110.0)
        .with_low(100.0)
        .created_at(datetime(2026, 1, 1, 9, 15))
        .build()
    )
    latest_order_block = (
        OrderBlockBuilder()
        .bearish()
        .with_high(130.0)
        .with_low(120.0)
        .created_at(datetime(2026, 1, 1, 9, 30))
        .build()
    )
    context = (
        StrategyContextBuilder()
        .with_order_blocks(older_order_block, latest_order_block)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].entry_price == 125.0
    assert candidates[0].stop_loss == 130.0


def test_plan_uses_latest_bullish_fvg_for_long_signal_when_order_block_missing():
    signal = TradeSignalBuilder().long().build()
    older_fvg = (
        FairValueGapBuilder()
        .bullish()
        .with_high(110.0)
        .with_low(100.0)
        .created_at(10)
        .build()
    )
    latest_fvg = (
        FairValueGapBuilder()
        .bullish()
        .with_high(130.0)
        .with_low(120.0)
        .created_at(20)
        .build()
    )
    context = (
        StrategyContextBuilder()
        .with_fair_value_gaps(older_fvg, latest_fvg)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].entry_price == 125.0
    assert candidates[0].stop_loss == 120.0


def test_plan_uses_latest_bearish_fvg_for_short_signal_when_order_block_missing():
    signal = TradeSignalBuilder().short().build()
    older_fvg = (
        FairValueGapBuilder()
        .bearish()
        .with_high(110.0)
        .with_low(100.0)
        .created_at(10)
        .build()
    )
    latest_fvg = (
        FairValueGapBuilder()
        .bearish()
        .with_high(130.0)
        .with_low(120.0)
        .created_at(20)
        .build()
    )
    context = (
        StrategyContextBuilder()
        .with_fair_value_gaps(older_fvg, latest_fvg)
        .build()
    )

    candidates = SMCTradeCandidatePlanner().plan(
        signal=signal,
        context=context,
    )

    assert len(candidates) == 1
    assert candidates[0].entry_price == 125.0
    assert candidates[0].stop_loss == 130.0

