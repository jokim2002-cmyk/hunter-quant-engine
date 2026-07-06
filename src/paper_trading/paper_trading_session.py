"""
Paper Trading Session

Safe local paper trading coordinator only. no broker code. No real orders.
No external SDK. Not live market data. Not a profitability claim.
"""

from __future__ import annotations

from datetime import datetime

from src.paper_trading.paper_order_journal import (
    PaperOrderJournal,
    PaperOrderRecord,
    PaperOrderRequest,
)
from src.paper_trading.paper_position_state import (
    PaperPosition,
    PaperPositionState,
)
from src.paper_trading.paper_realized_exit_record import (
    PaperExitReason,
    PaperRealizedExitRecord,
    create_paper_realized_exit_record,
)


class PaperTradingSession:
    """
    Fake/local paper trading coordinator.

    Wires PaperOrderRequest -> PaperOrderJournal -> PaperPositionState.
    This class never places real orders and never calls external code.
    """

    _EXIT_ID_PREFIX = "PAPER-EXIT"

    def __init__(
        self,
        journal: PaperOrderJournal | None = None,
        position_state: PaperPositionState | None = None,
    ) -> None:
        self._journal = journal if journal is not None else PaperOrderJournal()
        self._position_state = (
            position_state if position_state is not None else PaperPositionState()
        )
        self._exit_records: list[PaperRealizedExitRecord] = []

    def submit_order(self, request: PaperOrderRequest) -> PaperOrderRecord:
        """
        Record a fake BUY paper order and apply it to paper position state.
        """
        side = getattr(request, "side", "buy")
        if isinstance(side, str) and side.strip().lower() != "buy":
            raise ValueError("only BUY paper order requests are accepted")

        record = self._journal.record(request)
        self._position_state.apply_order(record)
        return record

    def list_orders(self) -> tuple[PaperOrderRecord, ...]:
        """
        Return all recorded fake paper orders in insertion order.
        """
        return self._journal.all_records()

    def list_open_positions(self) -> tuple[PaperPosition, ...]:
        """
        Return all open fake paper positions.
        """
        return self._position_state.open_positions()

    def find_order(self, order_id: str) -> PaperOrderRecord | None:
        """
        Return the recorded fake paper order matching order_id.
        """
        return self._journal.find_by_order_id(order_id)

    def find_position(self, symbol: str) -> PaperPosition | None:
        """
        Return the open fake paper position for symbol.
        """
        return self._position_state.find_by_symbol(symbol)

    def total_open_quantity(self, symbol: str) -> int:
        """
        Return the open fake paper quantity for symbol.
        """
        return self._position_state.total_quantity(symbol)

    def close_position(self, symbol: str) -> PaperPosition | None:
        """
        Close and return the open fake paper position for symbol.

        Returns None when no open paper position exists for the symbol.
        """
        return self._position_state.close(symbol)

    def close_position_with_exit_record(
        self,
        symbol: str,
        closed_at: datetime,
        exit_reason: PaperExitReason = PaperExitReason.MANUAL,
        exit_price: float | None = None,
    ) -> PaperRealizedExitRecord | None:
        """
        Close a fake paper position and store a local realized exit snapshot.

        Returns None when no open paper position exists for the symbol.
        No real order is placed. Simulated P&L is available only when
        exit_price is supplied.
        """
        closed_position = self.close_position(symbol)
        if closed_position is None:
            return None

        exit_id = f"{self._EXIT_ID_PREFIX}-{len(self._exit_records) + 1:06d}"
        exit_record = create_paper_realized_exit_record(
            position=closed_position,
            exit_id=exit_id,
            closed_at=closed_at,
            exit_reason=exit_reason,
            exit_price=exit_price,
        )
        self._exit_records.append(exit_record)
        return exit_record

    def list_exit_records(self) -> tuple[PaperRealizedExitRecord, ...]:
        """
        Return all local realized paper exit records in insertion order.
        """
        return tuple(self._exit_records)

    def find_exit_record(self, exit_id: str) -> PaperRealizedExitRecord | None:
        """
        Return the local realized paper exit record matching exit_id.
        """
        for exit_record in self._exit_records:
            if exit_record.exit_id == exit_id:
                return exit_record
        return None
