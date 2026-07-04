"""
Tests for SMCStrategy.
"""

from datetime import datetime

from src.models.institutional_setup import InstitutionalSetup
from src.strategy.base_strategy import BaseStrategy
from src.strategy.confluence.base_confluence_engine import BaseConfluenceEngine
from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.smc_strategy import SMCStrategy
from tests.builders.models.bos_builder import BOSBuilder
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


class RecordingConfluenceEngine(
    BaseConfluenceEngine[SMCRuleSetResult, InstitutionalSetup]
):
    def __init__(
        self,
        long_setups: tuple[InstitutionalSetup, ...] = (),
        short_setups: tuple[InstitutionalSetup, ...] = (),
    ) -> None:
        self.long_setups = long_setups
        self.short_setups = short_setups
        self.calls: list[tuple[SignalType, datetime]] = []

    def generate(
        self,
        result: SMCRuleSetResult,
        direction: SignalType,
        created_at: datetime,
    ) -> tuple[InstitutionalSetup, ...]:
        self.calls.append((direction, created_at))

        if direction == SignalType.LONG:
            return self.long_setups

        if direction == SignalType.SHORT:
            return self.short_setups

        return ()


def _setup(
    direction: SignalType,
    created_at: datetime,
) -> InstitutionalSetup:
    return InstitutionalSetup(
        direction=direction,
        confidence=80.0,
        rationale=("Injected setup.",),
        created_at=created_at,
    )


def test_smc_strategy_implements_base_strategy_contract():
    strategy = SMCStrategy()

    assert isinstance(strategy, BaseStrategy)


def test_generates_long_signal_when_only_bullish_smc_setup_is_valid():
    analysis_time = datetime(2026, 3, 1)

    bullish_bos = BOSBuilder().bullish().build()
    buy_side_sweep = LiquiditySweepBuilder().buy_side().build()
    bullish_fvg = FairValueGapBuilder().bullish().build()

    context = (
        StrategyContextBuilder()
        .analysis_time(analysis_time)
        .with_bos(bullish_bos)
        .with_liquidity_sweeps(buy_side_sweep)
        .with_fair_value_gaps(bullish_fvg)
        .build()
    )

    result = SMCStrategy().generate(context)

    assert len(result) == 1

    signal = result[0]

    assert signal.signal_type == SignalType.LONG
    assert signal.strength == SignalStrength.MEDIUM
    assert signal.confidence == 0.75
    assert signal.rationale == (
        "Bullish SMC setup is valid.",
        "Bearish SMC setup is invalid.",
    )
    assert signal.created_at == analysis_time


def test_generates_short_signal_when_only_bearish_smc_setup_is_valid():
    analysis_time = datetime(2026, 3, 2)

    bearish_bos = BOSBuilder().bearish().build()
    sell_side_sweep = LiquiditySweepBuilder().sell_side().build()
    bearish_fvg = FairValueGapBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .analysis_time(analysis_time)
        .with_bos(bearish_bos)
        .with_liquidity_sweeps(sell_side_sweep)
        .with_fair_value_gaps(bearish_fvg)
        .build()
    )

    result = SMCStrategy().generate(context)

    assert len(result) == 1

    signal = result[0]

    assert signal.signal_type == SignalType.SHORT
    assert signal.strength == SignalStrength.MEDIUM
    assert signal.confidence == 0.75
    assert signal.rationale == (
        "Bearish SMC setup is valid.",
        "Bullish SMC setup is invalid.",
    )
    assert signal.created_at == analysis_time


def test_generates_neutral_signal_when_no_directional_setup_is_valid():
    analysis_time = datetime(2026, 3, 3)

    context = (
        StrategyContextBuilder()
        .analysis_time(analysis_time)
        .build()
    )

    result = SMCStrategy().generate(context)

    assert len(result) == 1

    signal = result[0]

    assert signal.signal_type == SignalType.NEUTRAL
    assert signal.strength == SignalStrength.WEAK
    assert signal.confidence == 0.0
    assert signal.rationale == (
        "No valid directional SMC setup exists.",
    )
    assert signal.created_at == analysis_time


def test_generates_neutral_signal_when_bullish_and_bearish_setups_conflict():
    analysis_time = datetime(2026, 3, 4)

    bullish_bos = BOSBuilder().bullish().build()
    bearish_bos = BOSBuilder().bearish().build()

    buy_side_sweep = LiquiditySweepBuilder().buy_side().build()
    sell_side_sweep = LiquiditySweepBuilder().sell_side().build()

    bullish_fvg = FairValueGapBuilder().bullish().build()
    bearish_fvg = FairValueGapBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .analysis_time(analysis_time)
        .with_bos(bullish_bos, bearish_bos)
        .with_liquidity_sweeps(buy_side_sweep, sell_side_sweep)
        .with_fair_value_gaps(bullish_fvg, bearish_fvg)
        .build()
    )

    result = SMCStrategy().generate(context)

    assert len(result) == 1

    signal = result[0]

    assert signal.signal_type == SignalType.NEUTRAL
    assert signal.strength == SignalStrength.WEAK
    assert signal.confidence == 0.0
    assert signal.rationale == (
        "Conflicting bullish and bearish SMC setups exist.",
    )
    assert signal.created_at == analysis_time


def test_generates_long_signal_when_bullish_setup_uses_choch_and_order_block():
    analysis_time = datetime(2026, 3, 5)

    from tests.builders.models.choch_builder import CHOCHBuilder
    from tests.builders.models.order_block_builder import OrderBlockBuilder

    bullish_choch = CHOCHBuilder().bullish().build()
    buy_side_sweep = LiquiditySweepBuilder().buy_side().build()
    bullish_order_block = OrderBlockBuilder().bullish().build()

    context = (
        StrategyContextBuilder()
        .analysis_time(analysis_time)
        .with_choch(bullish_choch)
        .with_liquidity_sweeps(buy_side_sweep)
        .with_order_blocks(bullish_order_block)
        .build()
    )

    result = SMCStrategy().generate(context)

    assert len(result) == 1

    signal = result[0]

    assert signal.signal_type == SignalType.LONG
    assert signal.strength == SignalStrength.MEDIUM
    assert signal.confidence == 0.75
    assert signal.created_at == analysis_time


def test_uses_injected_confluence_engine_for_directional_decision():
    analysis_time = datetime(2026, 3, 6)

    long_setup = _setup(
        direction=SignalType.LONG,
        created_at=analysis_time,
    )
    confluence_engine = RecordingConfluenceEngine(
        long_setups=(long_setup,),
        short_setups=(),
    )

    context = (
        StrategyContextBuilder()
        .analysis_time(analysis_time)
        .build()
    )

    result = SMCStrategy(
        confluence_engine=confluence_engine,
    ).generate(context)

    assert len(result) == 1
    assert result[0].signal_type == SignalType.LONG
    assert confluence_engine.calls == [
        (SignalType.LONG, analysis_time),
        (SignalType.SHORT, analysis_time),
    ]
