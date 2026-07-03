"""
Tests for TradeResult.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from src.backtesting.trade_result import TradeResult
from src.strategy.signal_type import SignalType


def test_trade_result_can_be_created():
    opened = datetime(2026, 1, 1, 10, 0)
    closed = datetime(2026, 1, 1, 11, 0)

    result = TradeResult(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        exit_price=110.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size=20.0,
        pnl=200.0,
        risk_multiple=2.0,
        opened_at=opened,
        closed_at=closed,
    )

    assert result.signal_type is SignalType.LONG
    assert result.entry_price == 100.0
    assert result.exit_price == 110.0
    assert result.stop_loss == 95.0
    assert result.take_profit == 110.0
    assert result.position_size == 20.0
    assert result.pnl == 200.0
    assert result.risk_multiple == 2.0
    assert result.opened_at == opened
    assert result.closed_at == closed


def test_trade_result_is_immutable():
    result = TradeResult(
        signal_type=SignalType.SHORT,
        entry_price=100.0,
        exit_price=90.0,
        stop_loss=105.0,
        take_profit=90.0,
        position_size=20.0,
        pnl=200.0,
        risk_multiple=2.0,
        opened_at=datetime(2026, 1, 1),
        closed_at=datetime(2026, 1, 2),
    )

    with pytest.raises(FrozenInstanceError):
        result.pnl = 300.0
