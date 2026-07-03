"""
Tests for SMCRuleSetResult.
"""

from dataclasses import FrozenInstanceError

import pytest

from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult
from tests.builders.models.bos_builder import BOSBuilder
from tests.builders.models.choch_builder import CHOCHBuilder
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder
from tests.builders.models.order_block_builder import OrderBlockBuilder


def test_smc_rule_set_result_can_be_created():
    bos = BOSBuilder().bullish().build()
    choch = CHOCHBuilder().bullish().build()
    sweep = LiquiditySweepBuilder().buy_side().build()
    fvg = FairValueGapBuilder().bullish().build()
    order_block = OrderBlockBuilder().bullish().build()

    result = SMCRuleSetResult(
        bos_events=(bos,),
        choch_events=(choch,),
        liquidity_sweeps=(sweep,),
        fair_value_gaps=(fvg,),
        order_blocks=(order_block,),
    )

    assert result.bos_events == (bos,)
    assert result.choch_events == (choch,)
    assert result.liquidity_sweeps == (sweep,)
    assert result.fair_value_gaps == (fvg,)
    assert result.order_blocks == (order_block,)


def test_smc_rule_set_result_can_be_empty():
    result = SMCRuleSetResult(
        bos_events=(),
        choch_events=(),
        liquidity_sweeps=(),
        fair_value_gaps=(),
        order_blocks=(),
    )

    assert result.bos_events == ()
    assert result.choch_events == ()
    assert result.liquidity_sweeps == ()
    assert result.fair_value_gaps == ()
    assert result.order_blocks == ()


def test_smc_rule_set_result_is_immutable():
    result = SMCRuleSetResult(
        bos_events=(),
        choch_events=(),
        liquidity_sweeps=(),
        fair_value_gaps=(),
        order_blocks=(),
    )

    with pytest.raises(FrozenInstanceError):
        result.bos_events = ()
