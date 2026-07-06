"""
Paper Trading Replay Loop

Safe local replay helper for fake/paper trading only.

This module processes deterministic replay steps through PaperTradingSession.
No broker code. No real orders. Not live market data. Not a profitability claim.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from src.paper_trading.paper_order_journal import (
    PaperOrderRecord,
    PaperOrderRequest,
)
from src.paper_trading.paper_realized_exit_record import (
    PaperExitReason,
    PaperRealizedExitRecord,
)
from src.paper_trading.paper_trading_session import PaperTradingSession


@dataclass(frozen=True)
class PaperTradingReplayStep:
    """
    One deterministic fake/paper replay step.

    A step may submit one PaperOrderRequest, close one existing symbol, or do
    both in order. It is local replay only and never connects to a broker.
    """

    timestamp: datetime
    request: PaperOrderRequest | None = None
    close_symbol: str = ""
    exit_reason: PaperExitReason = PaperExitReason.MANUAL
    exit_price: float | None = None
    estimated_exit_charges: float = 0.0
    estimated_slippage: float = 0.0
    note: str = ""

    def __post_init__(self) -> None:
        has_request = self.request is not None
        has_close = bool(self.close_symbol.strip())

        if not has_request and not has_close:
            raise ValueError("replay step requires a request or close_symbol")
        if self.request is not None and not isinstance(
            self.request, PaperOrderRequest
        ):
            raise ValueError("request must be a PaperOrderRequest")
        if not isinstance(self.exit_reason, PaperExitReason):
            raise ValueError("exit_reason must be a PaperExitReason")
        if self.exit_price is not None and self.exit_price <= 0:
            raise ValueError("exit_price must be greater than 0")
        if self.estimated_exit_charges < 0:
            raise ValueError("estimated_exit_charges cannot be negative")
        if self.estimated_slippage < 0:
            raise ValueError("estimated_slippage cannot be negative")
        if not has_close and (
            self.exit_price is not None
            or self.estimated_exit_charges
            or self.estimated_slippage
        ):
            raise ValueError("exit details require close_symbol")


@dataclass(frozen=True)
class PaperTradingReplayResult:
    """
    Result of a deterministic fake/paper replay run.
    """

    session: PaperTradingSession
    submitted_orders: tuple[PaperOrderRecord, ...]
    exit_records: tuple[PaperRealizedExitRecord, ...]
    missing_close_symbols: tuple[str, ...]
    processed_steps: int

    @property
    def has_missing_closes(self) -> bool:
        """
        Return True when a replay close step had no matching open position.
        """
        return bool(self.missing_close_symbols)

    @property
    def submitted_orders_count(self) -> int:
        """
        Return the number of fake/paper orders submitted during replay.
        """
        return len(self.submitted_orders)

    @property
    def exit_records_count(self) -> int:
        """
        Return the number of fake/paper exits created during replay.
        """
        return len(self.exit_records)


def run_paper_trading_replay_loop(
    steps: Iterable[PaperTradingReplayStep],
    session: PaperTradingSession | None = None,
) -> PaperTradingReplayResult:
    """
    Run deterministic fake/paper replay steps through a PaperTradingSession.

    The loop submits requests first and then closes the requested symbol for
    each step. It records missing closes instead of failing the whole replay.
    """
    paper_session = session or PaperTradingSession()
    submitted_orders: list[PaperOrderRecord] = []
    exit_records: list[PaperRealizedExitRecord] = []
    missing_close_symbols: list[str] = []
    processed_steps = 0

    for step in steps:
        processed_steps += 1

        if step.request is not None:
            submitted_orders.append(paper_session.submit_order(step.request))

        close_symbol = step.close_symbol.strip()
        if close_symbol:
            exit_record = paper_session.close_position_with_exit_record(
                close_symbol,
                closed_at=step.timestamp,
                exit_reason=step.exit_reason,
                exit_price=step.exit_price,
                estimated_exit_charges=step.estimated_exit_charges,
                estimated_slippage=step.estimated_slippage,
            )
            if exit_record is None:
                missing_close_symbols.append(close_symbol)
            else:
                exit_records.append(exit_record)

    return PaperTradingReplayResult(
        session=paper_session,
        submitted_orders=tuple(submitted_orders),
        exit_records=tuple(exit_records),
        missing_close_symbols=tuple(missing_close_symbols),
        processed_steps=processed_steps,
    )
