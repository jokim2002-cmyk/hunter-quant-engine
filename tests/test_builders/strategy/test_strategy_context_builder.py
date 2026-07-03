"""
Tests for StrategyContextBuilder.
"""

from datetime import datetime

from tests.builders.models.bos_builder import BOSBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_builds_default_strategy_context():
    context = StrategyContextBuilder().build()

    assert context.symbol == "TEST"
    assert context.timeframe == "1H"
    assert context.bos_events == ()
    assert context.choch_events == ()
    assert context.fair_value_gaps == ()
    assert context.order_blocks == ()


def test_overrides_scalar_values():
    analysis_time = datetime(2026, 7, 4)

    context = (
        StrategyContextBuilder()
        .symbol("NIFTY")
        .timeframe("15M")
        .analysis_time(analysis_time)
        .build()
    )

    assert context.symbol == "NIFTY"
    assert context.timeframe == "15M"
    assert context.analysis_time == analysis_time


def test_adds_multiple_bos_events():
    bullish = BOSBuilder().bullish().build()
    bearish = BOSBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_bos(bullish, bearish)
        .build()
    )

    assert context.bos_events == (bullish, bearish)
