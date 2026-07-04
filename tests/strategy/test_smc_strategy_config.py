"""
SMC Strategy Config Tests
"""

from datetime import datetime

from src.config.strategy_config import (
    DEFAULT_SMC_STRATEGY_CONFIG,
    SMCStrategyConfig,
    StrategyMode,
)
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.smc_strategy import SMCStrategy
from tests.builders.models.bos_builder import BOSBuilder
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_smc_strategy_uses_default_config_when_none_is_provided():
    strategy = SMCStrategy()

    assert strategy.config == DEFAULT_SMC_STRATEGY_CONFIG


def test_smc_strategy_uses_custom_config_for_directional_signal():
    analysis_time = datetime(2026, 3, 7)
    config = SMCStrategyConfig(
        mode=StrategyMode.RELAXED,
        directional_signal_strength=SignalStrength.WEAK,
        directional_signal_confidence=0.6,
    )

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

    result = SMCStrategy(config=config).generate(context)

    assert len(result) == 1
    assert result[0].signal_type is SignalType.LONG
    assert result[0].strength is SignalStrength.WEAK
    assert result[0].confidence == 0.6
    assert result[0].created_at == analysis_time


def test_smc_strategy_uses_custom_config_for_neutral_signal():
    analysis_time = datetime(2026, 3, 8)
    config = SMCStrategyConfig(
        neutral_signal_strength=SignalStrength.MEDIUM,
        neutral_signal_confidence=0.25,
    )

    context = (
        StrategyContextBuilder()
        .analysis_time(analysis_time)
        .build()
    )

    result = SMCStrategy(config=config).generate(context)

    assert len(result) == 1
    assert result[0].signal_type is SignalType.NEUTRAL
    assert result[0].strength is SignalStrength.MEDIUM
    assert result[0].confidence == 0.25
    assert result[0].created_at == analysis_time


def test_smc_strategy_can_skip_neutral_signals_when_configured():
    analysis_time = datetime(2026, 3, 9)
    config = SMCStrategyConfig(
        emit_neutral_signal=False,
    )

    context = (
        StrategyContextBuilder()
        .analysis_time(analysis_time)
        .build()
    )

    result = SMCStrategy(config=config).generate(context)

    assert result == ()
