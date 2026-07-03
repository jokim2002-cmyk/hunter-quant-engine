"""
Tests for SMCSetupValidator.
"""

from src.strategy.setup_validators.base_setup_validator import BaseSetupValidator
from src.strategy.setup_validators.smc_setup_validator import SMCSetupValidator
from tests.builders.models.bos_builder import BOSBuilder
from tests.builders.models.choch_builder import CHOCHBuilder
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder
from tests.builders.models.order_block_builder import OrderBlockBuilder
from tests.builders.strategy.smc_rule_set_result_builder import SMCRuleSetResultBuilder


def test_smc_setup_validator_implements_base_setup_validator_contract():
    validator = SMCSetupValidator()

    assert isinstance(validator, BaseSetupValidator)


def test_returns_true_when_bos_sweep_and_fvg_exist():
    bos = BOSBuilder().bullish().build()
    sweep = LiquiditySweepBuilder().buy_side().build()
    fvg = FairValueGapBuilder().bullish().build()

    result = (
        SMCRuleSetResultBuilder()
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .build()
    )

    assert SMCSetupValidator().is_valid(result) is True


def test_returns_true_when_choch_sweep_and_order_block_exist():
    choch = CHOCHBuilder().bullish().build()
    sweep = LiquiditySweepBuilder().buy_side().build()
    order_block = OrderBlockBuilder().bullish().build()

    result = (
        SMCRuleSetResultBuilder()
        .with_choch(choch)
        .with_liquidity_sweeps(sweep)
        .with_order_blocks(order_block)
        .build()
    )

    assert SMCSetupValidator().is_valid(result) is True


def test_returns_false_when_market_structure_is_missing():
    sweep = LiquiditySweepBuilder().buy_side().build()
    fvg = FairValueGapBuilder().bullish().build()

    result = (
        SMCRuleSetResultBuilder()
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .build()
    )

    assert SMCSetupValidator().is_valid(result) is False


def test_returns_false_when_liquidity_sweep_is_missing():
    bos = BOSBuilder().bullish().build()
    fvg = FairValueGapBuilder().bullish().build()

    result = (
        SMCRuleSetResultBuilder()
        .with_bos(bos)
        .with_fair_value_gaps(fvg)
        .build()
    )

    assert SMCSetupValidator().is_valid(result) is False


def test_returns_false_when_entry_zone_is_missing():
    bos = BOSBuilder().bullish().build()
    sweep = LiquiditySweepBuilder().buy_side().build()

    result = (
        SMCRuleSetResultBuilder()
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .build()
    )

    assert SMCSetupValidator().is_valid(result) is False


def test_returns_false_for_empty_result():
    result = SMCRuleSetResultBuilder().build()

    assert SMCSetupValidator().is_valid(result) is False
