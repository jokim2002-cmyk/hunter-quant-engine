"""
Paper Realized Exit Record

Fake/local paper trading exit snapshots only. No real orders. No broker code.
No external SDK. Not live market data. Not a profitability claim.

This model records that a fake paper position was closed locally.
It does not calculate P&L because real exit premium, costs, and backtest data
are not part of this model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.paper_trading.paper_position_state import PaperPosition


class PaperExitReason(Enum):
    """
    Local reason for closing a fake paper position.
    """

    MANUAL = "manual"
    TARGET = "target"
    STOP_LOSS = "stop_loss"


@dataclass(frozen=True)
class PaperRealizedExitRecord:
    """
    Immutable local snapshot of a closed fake paper position.

    This is a paper-only record. It does not place orders and does not claim
    any profit or loss.
    """

    exit_id: str
    symbol: str
    quantity: int
    average_entry_price: float
    opened_at: datetime
    closed_at: datetime
    exit_reason: PaperExitReason
    source: str = "paper"

    def __post_init__(self) -> None:
        if not self.exit_id.strip():
            raise ValueError("exit_id is required")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        if self.average_entry_price <= 0:
            raise ValueError("average_entry_price must be greater than 0")
        if self.closed_at < self.opened_at:
            raise ValueError("closed_at must be after or equal to opened_at")
        if not isinstance(self.exit_reason, PaperExitReason):
            raise ValueError("exit_reason must be PaperExitReason")
        if self.source != "paper":
            raise ValueError("source must be 'paper'")


def create_paper_realized_exit_record(
    position: PaperPosition,
    exit_id: str,
    closed_at: datetime,
    exit_reason: PaperExitReason = PaperExitReason.MANUAL,
) -> PaperRealizedExitRecord:
    """
    Create a local paper exit snapshot from a closed paper position.

    No real order is placed. No P&L is calculated here.
    """
    return PaperRealizedExitRecord(
        exit_id=exit_id,
        symbol=position.symbol,
        quantity=position.quantity,
        average_entry_price=position.average_entry_price,
        opened_at=position.opened_at,
        closed_at=closed_at,
        exit_reason=exit_reason,
        source=position.source,
    )
