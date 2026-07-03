from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from src.strategy.strategy_context import StrategyContext


def test_strategy_context_can_be_created_empty():
    analysis_time = datetime(2026, 1, 1, 9, 15)

    context = StrategyContext(
        symbol="BTCUSDT",
        timeframe="M15",
        analysis_time=analysis_time,
        candles=(),
        market_structure_points=(),
        bos_events=(),
        choch_events=(),
        liquidity_points=(),
        equal_high_points=(),
        equal_low_points=(),
        liquidity_clusters=(),
        liquidity_sweeps=(),
        fair_value_gaps=(),
        order_blocks=(),
    )

    assert context.symbol == "BTCUSDT"
    assert context.timeframe == "M15"
    assert context.analysis_time == analysis_time
    assert context.candles == ()
    assert context.market_structure_points == ()
    assert context.bos_events == ()
    assert context.choch_events == ()
    assert context.liquidity_points == ()
    assert context.equal_high_points == ()
    assert context.equal_low_points == ()
    assert context.liquidity_clusters == ()
    assert context.liquidity_sweeps == ()
    assert context.fair_value_gaps == ()
    assert context.order_blocks == ()


def test_strategy_context_is_immutable():
    context = StrategyContext(
        symbol="BTCUSDT",
        timeframe="M15",
        analysis_time=datetime(2026, 1, 1, 9, 15),
        candles=(),
        market_structure_points=(),
        bos_events=(),
        choch_events=(),
        liquidity_points=(),
        equal_high_points=(),
        equal_low_points=(),
        liquidity_clusters=(),
        liquidity_sweeps=(),
        fair_value_gaps=(),
        order_blocks=(),
    )

    with pytest.raises(FrozenInstanceError):
        context.symbol = "ETHUSDT"
