"""
Trade Plan Deduplicator Tests
"""

from datetime import datetime

from src.backtesting.trade_plan_deduplicator import TradePlanDeduplicator
from src.risk.trade_plan import TradePlan
from src.strategy.signal_type import SignalType


def _long_trade_plan(
    created_at: datetime,
    entry_price: float = 100.0,
    stop_loss: float = 96.0,
    take_profit: float = 108.0,
) -> TradePlan:
    return TradePlan(
        signal_type=SignalType.LONG,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_size=25.0,
        risk_amount=100.0,
        reward_amount=200.0,
        created_at=created_at,
    )


def _short_trade_plan(
    created_at: datetime,
    entry_price: float = 100.0,
    stop_loss: float = 104.0,
    take_profit: float = 92.0,
) -> TradePlan:
    return TradePlan(
        signal_type=SignalType.SHORT,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_size=25.0,
        risk_amount=100.0,
        reward_amount=200.0,
        created_at=created_at,
    )


def test_deduplicate_returns_empty_tuple_for_empty_input():
    deduplicator = TradePlanDeduplicator()

    assert deduplicator.deduplicate(()) == ()


def test_deduplicate_removes_same_direction_and_same_trade_levels():
    first_plan = _long_trade_plan(datetime(2026, 1, 1, 9, 15))
    duplicate_plan = _long_trade_plan(datetime(2026, 1, 1, 9, 20))

    deduplicator = TradePlanDeduplicator()

    result = deduplicator.deduplicate((first_plan, duplicate_plan))

    assert result == (first_plan,)


def test_deduplicate_preserves_first_occurrence_order():
    first_plan = _long_trade_plan(datetime(2026, 1, 1, 9, 15))
    second_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 20),
        entry_price=110.0,
        stop_loss=106.0,
        take_profit=118.0,
    )
    duplicate_first_plan = _long_trade_plan(datetime(2026, 1, 1, 9, 25))

    deduplicator = TradePlanDeduplicator()

    result = deduplicator.deduplicate(
        (
            first_plan,
            second_plan,
            duplicate_first_plan,
        )
    )

    assert result == (first_plan, second_plan)


def test_deduplicate_keeps_different_signal_types():
    long_plan = _long_trade_plan(datetime(2026, 1, 1, 9, 15))
    short_plan = _short_trade_plan(datetime(2026, 1, 1, 9, 20))

    deduplicator = TradePlanDeduplicator()

    result = deduplicator.deduplicate((long_plan, short_plan))

    assert result == (long_plan, short_plan)


def test_deduplicate_keeps_different_entry_price():
    first_plan = _long_trade_plan(datetime(2026, 1, 1, 9, 15))
    second_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 20),
        entry_price=101.0,
        stop_loss=96.0,
        take_profit=108.0,
    )

    deduplicator = TradePlanDeduplicator()

    result = deduplicator.deduplicate((first_plan, second_plan))

    assert result == (first_plan, second_plan)


def test_deduplicate_keeps_different_stop_loss():
    first_plan = _long_trade_plan(datetime(2026, 1, 1, 9, 15))
    second_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 20),
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=108.0,
    )

    deduplicator = TradePlanDeduplicator()

    result = deduplicator.deduplicate((first_plan, second_plan))

    assert result == (first_plan, second_plan)


def test_deduplicate_keeps_different_take_profit():
    first_plan = _long_trade_plan(datetime(2026, 1, 1, 9, 15))
    second_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 20),
        entry_price=100.0,
        stop_loss=96.0,
        take_profit=109.0,
    )

    deduplicator = TradePlanDeduplicator()

    result = deduplicator.deduplicate((first_plan, second_plan))

    assert result == (first_plan, second_plan)


def test_deduplicate_uses_price_precision():
    first_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 15),
        entry_price=100.00001,
    )
    duplicate_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 20),
        entry_price=100.00002,
    )

    deduplicator = TradePlanDeduplicator(price_precision=4)

    result = deduplicator.deduplicate((first_plan, duplicate_plan))

    assert result == (first_plan,)
