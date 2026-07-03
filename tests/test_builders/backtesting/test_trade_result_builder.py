"""
Tests for TradeResultBuilder.
"""

from datetime import datetime

from src.strategy.signal_type import SignalType
from tests.builders.backtesting.trade_result_builder import TradeResultBuilder


def test_trade_result_builder_creates_default_trade_result():
    result = TradeResultBuilder().build()

    assert result.signal_type is SignalType.LONG
    assert result.entry_price == 100.0
    assert result.exit_price == 110.0
    assert result.stop_loss == 95.0
    assert result.take_profit == 110.0
    assert result.position_size == 20.0
    assert result.pnl == 200.0
    assert result.risk_multiple == 2.0


def test_trade_result_builder_allows_custom_values():
    opened_at = datetime(2026, 1, 2, 10, 0)
    closed_at = datetime(2026, 1, 2, 12, 0)

    result = (
        TradeResultBuilder()
        .with_signal_type(SignalType.SHORT)
        .with_entry_price(200.0)
        .with_exit_price(180.0)
        .with_stop_loss(210.0)
        .with_take_profit(180.0)
        .with_position_size(10.0)
        .with_pnl(200.0)
        .with_risk_multiple(2.0)
        .with_opened_at(opened_at)
        .with_closed_at(closed_at)
        .build()
    )

    assert result.signal_type is SignalType.SHORT
    assert result.entry_price == 200.0
    assert result.exit_price == 180.0
    assert result.stop_loss == 210.0
    assert result.take_profit == 180.0
    assert result.position_size == 10.0
    assert result.pnl == 200.0
    assert result.risk_multiple == 2.0
    assert result.opened_at == opened_at
    assert result.closed_at == closed_at
