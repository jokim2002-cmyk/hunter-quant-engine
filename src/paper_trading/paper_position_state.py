"""
Paper Position State

Fake/local paper trading position tracking only. No real orders. No broker code.
No broker SDK. Not live market data. Not a profitability claim.

Provides:
- PaperPosition      — immutable snapshot of one open fake paper position.
- PaperPositionState — in-memory state of all open fake paper positions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.paper_trading.paper_order_journal import PaperOrderRecord, PaperOrderStatus


@dataclass(frozen=True)
class PaperPosition:
    """
    An immutable snapshot of one open fake paper position.

    source is always 'paper' to make clear this is not a real position.
    No broker code. No real orders. Not a profitability claim.
    """

    symbol: str
    quantity: int
    average_entry_price: float
    opened_at: datetime
    source: str = "paper"

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        if self.average_entry_price <= 0:
            raise ValueError("average_entry_price must be greater than 0")
        if self.source != "paper":
            raise ValueError("source must be 'paper'")


class PaperPositionState:
    """
    In-memory state of all open fake paper positions.

    Accepts PaperOrderRecord objects with status OPEN and source 'paper'.
    Merges duplicate symbols using weighted average entry price.

    This class never places real orders, never calls broker code,
    and never imports any broker SDK.
    Not a profitability claim.
    """

    def __init__(self) -> None:
        self._positions: dict[str, PaperPosition] = {}

    def apply_order(self, record: PaperOrderRecord) -> PaperPosition:
        """
        Open or update a fake paper position from a PaperOrderRecord.

        Only OPEN status records with source 'paper' are accepted.
        Duplicate symbols are merged using weighted average entry price.
        Returns the resulting PaperPosition. No real order is placed.
        """
        if record.source != "paper":
            raise ValueError("only paper source records are accepted")
        if record.status is not PaperOrderStatus.OPEN:
            raise ValueError("only OPEN status records can open a position")
        if not record.symbol.strip():
            raise ValueError("symbol is required")
        if record.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        if record.planned_entry_price <= 0:
            raise ValueError("planned_entry_price must be greater than 0")

        existing = self._positions.get(record.symbol)
        if existing is None:
            position = PaperPosition(
                symbol=record.symbol,
                quantity=record.quantity,
                average_entry_price=record.planned_entry_price,
                opened_at=record.created_at,
            )
        else:
            total_qty = existing.quantity + record.quantity
            weighted_price = (
                existing.quantity * existing.average_entry_price
                + record.quantity * record.planned_entry_price
            ) / total_qty
            position = PaperPosition(
                symbol=existing.symbol,
                quantity=total_qty,
                average_entry_price=weighted_price,
                opened_at=existing.opened_at,
            )

        self._positions[record.symbol] = position
        return position

    def open_positions(self) -> tuple[PaperPosition, ...]:
        """
        Return all open fake paper positions in insertion order.
        """
        return tuple(self._positions.values())

    def find_by_symbol(self, symbol: str) -> PaperPosition | None:
        """
        Return the open position for symbol, or None if not found.
        """
        return self._positions.get(symbol)

    def total_quantity(self, symbol: str) -> int:
        """
        Return total open quantity for symbol, or 0 if no position exists.
        """
        position = self._positions.get(symbol)
        return position.quantity if position is not None else 0

    def close(self, symbol: str) -> PaperPosition | None:
        """
        Remove and return the open position for symbol, or None if not found.
        """
        return self._positions.pop(symbol, None)
