"""
Tests for SMCRuleSetResultBuilder.
"""

from tests.builders.models.bos_builder import BOSBuilder
from tests.builders.models.choch_builder import CHOCHBuilder
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder
from tests.builders.models.order_block_builder import OrderBlockBuilder
from tests.builders.strategy.smc_rule_set_result_builder import SMCRuleSetResultBuilder


def test_builds_empty_smc_rule_set_result_by_default():
    result = SMCRuleSetResultBuilder().build()

    assert result.bos_events == ()
    assert result.choch_events == ()
    assert result.liquidity_sweeps == ()
    assert result.fair_value_gaps == ()
    assert result.order_blocks == ()


def test_builds_smc_rule_set_result_with_bos_events():
    bos = BOSBuilder().bullish().build()

    result = SMCRuleSetResultBuilder().with_bos(bos).build()

    assert result.bos_events == (bos,)


def test_builds_smc_rule_set_result_with_choch_events():
    choch = CHOCHBuilder().bullish().build()

    result = SMCRuleSetResultBuilder().with_choch(choch).build()

    assert result.choch_events == (choch,)


def test_builds_smc_rule_set_result_with_liquidity_sweeps():
    sweep = LiquiditySweepBuilder().buy_side().build()

    result = SMCRuleSetResultBuilder().with_liquidity_sweeps(sweep).build()

    assert result.liquidity_sweeps == (sweep,)


def test_builds_smc_rule_set_result_with_fair_value_gaps():
    fvg = FairValueGapBuilder().bullish().build()

    result = SMCRuleSetResultBuilder().with_fair_value_gaps(fvg).build()

    assert result.fair_value_gaps == (fvg,)


def test_builds_smc_rule_set_result_with_order_blocks():
    order_block = OrderBlockBuilder().bullish().build()

    result = SMCRuleSetResultBuilder().with_order_blocks(order_block).build()

    assert result.order_blocks == (order_block,)


def test_collection_methods_accept_multiple_events():
    bos_1 = BOSBuilder().bullish().build()
    bos_2 = BOSBuilder().bullish().build()

    result = SMCRuleSetResultBuilder().with_bos(bos_1, bos_2).build()

    assert result.bos_events == (bos_1, bos_2)
