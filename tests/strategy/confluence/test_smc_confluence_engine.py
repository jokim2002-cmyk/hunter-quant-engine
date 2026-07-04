"""
SMC Confluence Engine Tests
"""

from datetime import datetime

from src.models.institutional_setup import InstitutionalSetup
from src.strategy.confluence.base_confluence_engine import BaseConfluenceEngine
from src.strategy.confluence.smc_confluence_engine import SMCConfluenceEngine
from src.strategy.signal_type import SignalType
from tests.builders.models.bos_builder import BOSBuilder
from tests.builders.models.choch_builder import CHOCHBuilder
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder
from tests.builders.models.order_block_builder import OrderBlockBuilder
from tests.builders.strategy.smc_rule_set_result_builder import (
    SMCRuleSetResultBuilder,
)


def test_smc_confluence_engine_implements_base_confluence_engine_contract():
    engine = SMCConfluenceEngine()

    assert isinstance(engine, BaseConfluenceEngine)


def test_returns_empty_tuple_when_result_is_not_valid():
    result = SMCRuleSetResultBuilder().build()

    setups = SMCConfluenceEngine().generate(
        result=result,
        direction=SignalType.LONG,
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setups == ()


def test_returns_empty_tuple_for_neutral_direction():
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

    setups = SMCConfluenceEngine().generate(
        result=result,
        direction=SignalType.NEUTRAL,
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setups == ()


def test_generates_long_institutional_setup_from_bullish_confluence():
    created_at = datetime(2026, 1, 1, 9, 0)
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

    setups = SMCConfluenceEngine().generate(
        result=result,
        direction=SignalType.LONG,
        created_at=created_at,
    )

    assert len(setups) == 1
    assert isinstance(setups[0], InstitutionalSetup)
    assert setups[0].direction is SignalType.LONG
    assert setups[0].created_at == created_at
    assert setups[0].bos_event == bos
    assert setups[0].liquidity_sweep == sweep
    assert setups[0].fair_value_gap == fvg
    assert setups[0].order_block is None
    assert setups[0].is_actionable() is True


def test_generates_short_institutional_setup_from_bearish_confluence():
    created_at = datetime(2026, 1, 1, 9, 0)
    choch = CHOCHBuilder().bearish().build()
    sweep = LiquiditySweepBuilder().sell_side().build()
    order_block = OrderBlockBuilder().bearish().build()

    result = (
        SMCRuleSetResultBuilder()
        .with_choch(choch)
        .with_liquidity_sweeps(sweep)
        .with_order_blocks(order_block)
        .build()
    )

    setups = SMCConfluenceEngine().generate(
        result=result,
        direction=SignalType.SHORT,
        created_at=created_at,
    )

    assert len(setups) == 1
    assert setups[0].direction is SignalType.SHORT
    assert setups[0].choch_event == choch
    assert setups[0].liquidity_sweep == sweep
    assert setups[0].fair_value_gap is None
    assert setups[0].order_block == order_block
    assert setups[0].is_actionable() is True


def test_confidence_is_80_when_single_entry_zone_exists():
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

    setups = SMCConfluenceEngine().generate(
        result=result,
        direction=SignalType.LONG,
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setups[0].confidence == 80.0


def test_confidence_is_100_when_fvg_and_order_block_both_exist():
    bos = BOSBuilder().bullish().build()
    sweep = LiquiditySweepBuilder().buy_side().build()
    fvg = FairValueGapBuilder().bullish().build()
    order_block = OrderBlockBuilder().bullish().build()

    result = (
        SMCRuleSetResultBuilder()
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .with_order_blocks(order_block)
        .build()
    )

    setups = SMCConfluenceEngine().generate(
        result=result,
        direction=SignalType.LONG,
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setups[0].confidence == 100.0


def test_rationale_describes_present_confluence_evidence():
    bos = BOSBuilder().bullish().build()
    sweep = LiquiditySweepBuilder().buy_side().build()
    fvg = FairValueGapBuilder().bullish().build()
    order_block = OrderBlockBuilder().bullish().build()

    result = (
        SMCRuleSetResultBuilder()
        .with_bos(bos)
        .with_liquidity_sweeps(sweep)
        .with_fair_value_gaps(fvg)
        .with_order_blocks(order_block)
        .build()
    )

    setups = SMCConfluenceEngine().generate(
        result=result,
        direction=SignalType.LONG,
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setups[0].rationale == (
        "LONG institutional SMC setup generated.",
        "BOS market structure evidence present.",
        "Liquidity sweep evidence present.",
        "Fair value gap entry zone evidence present.",
        "Order block entry zone evidence present.",
    )
