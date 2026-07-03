"""
Tests for BearishSMCRuleSet.
"""

from src.strategy.rule_sets.bearish_smc_rule_set import BearishSMCRuleSet
from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult
from tests.builders.models.bos_builder import BOSBuilder
from tests.builders.models.choch_builder import CHOCHBuilder
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder
from tests.builders.models.order_block_builder import OrderBlockBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_bearish_smc_rule_set_returns_typed_result():
    context = StrategyContextBuilder().build()

    result = BearishSMCRuleSet().evaluate(context)

    assert isinstance(result, SMCRuleSetResult)


def test_bearish_smc_rule_set_returns_only_bearish_smc_events():
    bullish_bos = BOSBuilder().bullish().build()
    bearish_bos = BOSBuilder().bearish().build()

    bullish_choch = CHOCHBuilder().bullish().build()
    bearish_choch = CHOCHBuilder().bearish().build()

    buy_side_sweep = LiquiditySweepBuilder().buy_side().build()
    sell_side_sweep = LiquiditySweepBuilder().sell_side().build()

    bullish_fvg = FairValueGapBuilder().bullish().build()
    bearish_fvg = FairValueGapBuilder().bearish().build()

    bullish_order_block = OrderBlockBuilder().bullish().build()
    bearish_order_block = OrderBlockBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_bos(bullish_bos, bearish_bos)
        .with_choch(bullish_choch, bearish_choch)
        .with_liquidity_sweeps(buy_side_sweep, sell_side_sweep)
        .with_fair_value_gaps(bullish_fvg, bearish_fvg)
        .with_order_blocks(bullish_order_block, bearish_order_block)
        .build()
    )

    result = BearishSMCRuleSet().evaluate(context)

    assert result.bos_events == (bearish_bos,)
    assert result.choch_events == (bearish_choch,)
    assert result.liquidity_sweeps == (sell_side_sweep,)
    assert result.fair_value_gaps == (bearish_fvg,)
    assert result.order_blocks == (bearish_order_block,)


def test_bearish_smc_rule_set_returns_empty_result_when_no_bearish_events_exist():
    bullish_bos = BOSBuilder().bullish().build()
    bullish_choch = CHOCHBuilder().bullish().build()
    buy_side_sweep = LiquiditySweepBuilder().buy_side().build()
    bullish_fvg = FairValueGapBuilder().bullish().build()
    bullish_order_block = OrderBlockBuilder().bullish().build()

    context = (
        StrategyContextBuilder()
        .with_bos(bullish_bos)
        .with_choch(bullish_choch)
        .with_liquidity_sweeps(buy_side_sweep)
        .with_fair_value_gaps(bullish_fvg)
        .with_order_blocks(bullish_order_block)
        .build()
    )

    result = BearishSMCRuleSet().evaluate(context)

    assert result.bos_events == ()
    assert result.choch_events == ()
    assert result.liquidity_sweeps == ()
    assert result.fair_value_gaps == ()
    assert result.order_blocks == ()


def test_bearish_smc_rule_set_returns_empty_result_for_empty_context():
    context = StrategyContextBuilder().build()

    result = BearishSMCRuleSet().evaluate(context)

    assert result.bos_events == ()
    assert result.choch_events == ()
    assert result.liquidity_sweeps == ()
    assert result.fair_value_gaps == ()
    assert result.order_blocks == ()
