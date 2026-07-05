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

def test_strict_config_requires_both_fvg_and_order_block():
    from src.config.strategy_config import STRICT_SMC_STRATEGY_CONFIG

    bos = BOSBuilder().bullish().build()
    sweep = LiquiditySweepBuilder().buy_side().build()
    fvg = FairValueGapBuilder().bullish().build()
    order_block = OrderBlockBuilder().bullish().build()

    result_without_order_block = (
        SMCRuleSetResultBuilder()
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .build()
    )
    complete_strict_result = (
        SMCRuleSetResultBuilder()
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .with_order_blocks(order_block)
        .build()
    )

    validator = SMCSetupValidator(config=STRICT_SMC_STRATEGY_CONFIG)

    assert validator.is_valid(result_without_order_block) is False
    assert validator.is_valid(complete_strict_result) is True


def test_relaxed_config_does_not_require_liquidity_sweep():
    from src.config.strategy_config import RELAXED_SMC_STRATEGY_CONFIG

    bos = BOSBuilder().bullish().build()
    fvg = FairValueGapBuilder().bullish().build()

    result = (
        SMCRuleSetResultBuilder()
        .with_bos(bos)
        .with_fair_value_gaps(fvg)
        .build()
    )

    assert SMCSetupValidator(config=RELAXED_SMC_STRATEGY_CONFIG).is_valid(result) is True

def test_returns_false_when_market_structure_evidence_is_stale():
    from src.config.strategy_config import SMCStrategyConfig

    config = SMCStrategyConfig(
        max_market_structure_age_candles=5,
        max_liquidity_sweep_age_candles=20,
        max_entry_zone_age_candles=20,
    )
    bos = BOSBuilder().bullish().at_index(10).build()
    sweep = LiquiditySweepBuilder().buy_side().created_at(20).build()
    fvg = FairValueGapBuilder().bullish().created_at(20).build()

    result = (
        SMCRuleSetResultBuilder()
        .analysis_index(20)
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .build()
    )

    assert SMCSetupValidator(config=config).is_valid(result) is False


def test_returns_false_when_liquidity_sweep_evidence_is_stale():
    from src.config.strategy_config import SMCStrategyConfig

    config = SMCStrategyConfig(
        max_market_structure_age_candles=20,
        max_liquidity_sweep_age_candles=5,
        max_entry_zone_age_candles=20,
    )
    bos = BOSBuilder().bullish().at_index(20).build()
    sweep = LiquiditySweepBuilder().buy_side().created_at(10).build()
    fvg = FairValueGapBuilder().bullish().created_at(20).build()

    result = (
        SMCRuleSetResultBuilder()
        .analysis_index(20)
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .build()
    )

    assert SMCSetupValidator(config=config).is_valid(result) is False


def test_returns_false_when_entry_zone_evidence_is_stale():
    from src.config.strategy_config import SMCStrategyConfig

    config = SMCStrategyConfig(
        max_market_structure_age_candles=20,
        max_liquidity_sweep_age_candles=20,
        max_entry_zone_age_candles=5,
    )
    bos = BOSBuilder().bullish().at_index(20).build()
    sweep = LiquiditySweepBuilder().buy_side().created_at(20).build()
    fvg = FairValueGapBuilder().bullish().created_at(10).build()

    result = (
        SMCRuleSetResultBuilder()
        .analysis_index(20)
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .build()
    )

    assert SMCSetupValidator(config=config).is_valid(result) is False


def test_returns_true_when_required_evidence_is_recent():
    from src.config.strategy_config import SMCStrategyConfig

    config = SMCStrategyConfig(
        max_market_structure_age_candles=5,
        max_liquidity_sweep_age_candles=5,
        max_entry_zone_age_candles=5,
    )
    bos = BOSBuilder().bullish().at_index(18).build()
    sweep = LiquiditySweepBuilder().buy_side().created_at(19).build()
    fvg = FairValueGapBuilder().bullish().created_at(20).build()

    result = (
        SMCRuleSetResultBuilder()
        .analysis_index(20)
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .build()
    )

    assert SMCSetupValidator(config=config).is_valid(result) is True


def test_relaxed_config_allows_older_evidence_than_strict_config():
    from src.config.strategy_config import (
        RELAXED_SMC_STRATEGY_CONFIG,
        STRICT_SMC_STRATEGY_CONFIG,
    )

    bos = BOSBuilder().bullish().at_index(40).build()
    sweep = LiquiditySweepBuilder().buy_side().created_at(40).build()
    fvg = FairValueGapBuilder().bullish().created_at(40).build()
    order_block = OrderBlockBuilder().bullish().at_index(40).build()

    result = (
        SMCRuleSetResultBuilder()
        .analysis_index(100)
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .with_order_blocks(order_block)
        .build()
    )

    assert SMCSetupValidator(config=STRICT_SMC_STRATEGY_CONFIG).is_valid(result) is False
    assert SMCSetupValidator(config=RELAXED_SMC_STRATEGY_CONFIG).is_valid(result) is True
