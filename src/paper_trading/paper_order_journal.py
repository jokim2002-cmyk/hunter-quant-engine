"""
Paper Order Journal

Fake/local paper trading records only. No real orders. No broker code.
No broker SDK. Not live market data. Not a profitability claim.

Provides:
- PaperOrderStatus  — lifecycle states for a paper order record.
- PaperOrderRequest — validated request to create a new paper order.
- PaperOrderRecord  — immutable record stored in the journal.
- PaperOrderJournal — in-memory journal that accepts requests and stores records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PaperOrderStatus(Enum):
    """
    Lifecycle status of a paper order record.

    Paper orders are fake/local records only. No real orders are placed.
    """

    OPEN = "open"
    CLOSED_TP = "closed_tp"
    CLOSED_SL = "closed_sl"
    CLOSED_MANUAL = "closed_manual"


@dataclass(frozen=True)
class PaperOrderRequest:
    """
    A validated request to record a new fake paper buy order.

    Option buying only. No option selling. No short CE/PE.
    No real orders. No broker code. Not a profitability claim.
    """

    symbol: str
    quantity: int
    planned_entry_price: float
    created_at: datetime
    plan_id: str = ""

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        if self.planned_entry_price <= 0:
            raise ValueError("planned_entry_price must be greater than 0")


@dataclass(frozen=True)
class PaperOrderRecord:
    """
    An immutable fake paper order record stored in the journal.

    source is always 'paper' to make clear this is not a real order.
    No broker code. No real orders. Not a profitability claim.
    """

    order_id: str
    symbol: str
    quantity: int
    planned_entry_price: float
    status: PaperOrderStatus
    created_at: datetime
    source: str
    plan_id: str = ""

    def __post_init__(self) -> None:
        if self.source != "paper":
            raise ValueError("source must be 'paper'")


class PaperOrderJournal:
    """
    In-memory journal of fake paper order records.

    Accepts PaperOrderRequest objects, assigns deterministic order IDs,
    and stores PaperOrderRecord objects in insertion order.

    This journal never places real orders, never calls broker code,
    and never imports any broker SDK.
    Not a profitability claim.
    """

    _ID_PREFIX = "PAPER"

    def __init__(self) -> None:
        self._records: list[PaperOrderRecord] = []
        self._counter: int = 0

    def record(self, request: PaperOrderRequest) -> PaperOrderRecord:
        """
        Accept a PaperOrderRequest and store a new PaperOrderRecord.

        Returns the stored record. No real order is placed.
        """
        self._counter += 1
        order_id = f"{self._ID_PREFIX}-{self._counter:06d}"
        record = PaperOrderRecord(
            order_id=order_id,
            symbol=request.symbol,
            quantity=request.quantity,
            planned_entry_price=request.planned_entry_price,
            status=PaperOrderStatus.OPEN,
            created_at=request.created_at,
            source="paper",
            plan_id=request.plan_id,
        )
        self._records.append(record)
        return record

    def all_records(self) -> tuple[PaperOrderRecord, ...]:
        """
        Return all stored records in insertion order.
        """
        return tuple(self._records)

    def find_by_order_id(self, order_id: str) -> PaperOrderRecord | None:
        """
        Return the record matching order_id, or None if not found.
        """
        for record in self._records:
            if record.order_id == order_id:
                return record
        return None
