"""
Tests for BearishBOSRule.
"""

from datetime import datetime

from src.models.bos_point import BOSPoint, BOSType
from src.models.swing_point import SwingPoint, SwingPointType
from src.strategy.rules.market_structure.bearish_bos_rule import BearishBOSRule
from src.strategy.strategy_context import StrategyContext


def create_swing() -> SwingPoint:
    return SwingPoint(
        index=1,
        timestamp=datetime.now(),
        price=100.0,
        swing_type=SwingPointType.SWING_HIGH,
    )


def create_bos(bos_type: BOSType) -> BOSPoint:
    return BOSPoint(
        index=2,
        timestamp=datetime.now(),
        break_price=101.0,
        bos_type=bos_type,
        broken_swing=create_swing(),
    )


def create_context(bos_events):
    return StrategyContext(
        symbol="TEST",
        timeframe="1H",
        analysis_time=datetime.now(),
        candles=(),
        market_structure_points=(),
        bos_events=tuple(bos_events),
        choch_events=(),
        liquidity_points=(),
        equal_high_points=(),
        equal_low_points=(),
        liquidity_clusters=(),
        liquidity_sweeps=(),
        fair_value_gaps=(),
        order_blocks=(),
    )


def test_returns_only_bearish_bos_events():
    bullish = create_bos(BOSType.BULLISH)
    bearish = create_bos(BOSType.BEARISH)

    context = create_context([bullish, bearish])

    result = BearishBOSRule().evaluate(context)

    assert result == (bearish,)


def test_returns_empty_tuple_when_no_bearish_bos_exists():
    bullish = create_bos(BOSType.BULLISH)

    context = create_context([bullish])

    result = BearishBOSRule().evaluate(context)

    assert result == ()
