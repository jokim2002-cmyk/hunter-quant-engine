"""
Paper trading session summary.

Creates local summary data from fake paper orders and open paper positions.
This module is local-only and does not execute orders.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperTradingSessionSummary:
    """
    Summary of a local paper trading session.
    """

    total_orders: int
    open_positions_count: int
    total_open_quantity: int
    symbols: tuple[str, ...]

    @property
    def has_open_positions(self) -> bool:
        """
        Return True when the session has at least one open paper position.
        """
        return self.open_positions_count > 0


def build_paper_trading_session_summary(session) -> PaperTradingSessionSummary:
    """
    Build a summary from a PaperTradingSession-like object.
    """
    orders = list(session.list_orders())
    positions = list(session.list_open_positions())

    symbols = tuple(position.symbol for position in positions)
    total_open_quantity = sum(position.quantity for position in positions)

    return PaperTradingSessionSummary(
        total_orders=len(orders),
        open_positions_count=len(positions),
        total_open_quantity=total_open_quantity,
        symbols=symbols,
    )
