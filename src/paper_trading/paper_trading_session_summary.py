"""
Paper Trading Session Summary

Safe local paper trading session summary only.
No broker code. No real orders. Not live market data. Not a profitability claim.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperTradingSessionSummary:
    """
    Trader-friendly local paper trading session summary.

    P&L values are paper-only simulation values. Net P&L includes only
    estimated charges/slippage.
    """

    total_orders: int
    open_positions_count: int
    total_open_quantity: int
    symbols: tuple[str, ...]
    closed_trades_count: int = 0
    exits_with_pnl_count: int = 0
    total_simulated_gross_pnl: float = 0.0
    total_estimated_costs: float = 0.0
    total_simulated_net_pnl: float = 0.0
    winning_exits_count: int = 0
    losing_exits_count: int = 0
    flat_exits_count: int = 0
    unknown_pnl_exits_count: int = 0
    net_winning_exits_count: int = 0
    net_losing_exits_count: int = 0
    net_flat_exits_count: int = 0
    unknown_net_pnl_exits_count: int = 0

    @property
    def has_open_positions(self) -> bool:
        """
        Return True when the session has open paper positions.
        """
        return self.open_positions_count > 0

    @property
    def has_closed_trades(self) -> bool:
        """
        Return True when at least one local paper exit record exists.
        """
        return self.closed_trades_count > 0

    @property
    def paper_pnl_is_simulation_only(self) -> bool:
        """
        Make the summary safety meaning explicit.
        """
        return True

    @property
    def estimated_costs_included_in_net_pnl(self) -> bool:
        """
        Return True because net P&L subtracts estimated charges/slippage.
        """
        return True

    @property
    def gross_pnl_excludes_costs(self) -> bool:
        """
        Return True because gross P&L is before costs.
        """
        return True


def build_paper_trading_session_summary(session) -> PaperTradingSessionSummary:
    """
    Build a local paper trading session summary.

    This reads only local paper orders, open positions, and exit records.
    """
    orders = session.list_orders()
    open_positions = session.list_open_positions()
    exit_records = session.list_exit_records()

    gross_pnl_values = [
        exit_record.simulated_gross_pnl
        for exit_record in exit_records
        if exit_record.simulated_gross_pnl is not None
    ]
    net_pnl_values = [
        exit_record.simulated_net_pnl
        for exit_record in exit_records
        if exit_record.simulated_net_pnl is not None
    ]

    winning_exits_count = len([value for value in gross_pnl_values if value > 0])
    losing_exits_count = len([value for value in gross_pnl_values if value < 0])
    flat_exits_count = len([value for value in gross_pnl_values if value == 0])
    unknown_pnl_exits_count = len(exit_records) - len(gross_pnl_values)

    net_winning_exits_count = len([value for value in net_pnl_values if value > 0])
    net_losing_exits_count = len([value for value in net_pnl_values if value < 0])
    net_flat_exits_count = len([value for value in net_pnl_values if value == 0])
    unknown_net_pnl_exits_count = len(exit_records) - len(net_pnl_values)

    return PaperTradingSessionSummary(
        total_orders=len(orders),
        open_positions_count=len(open_positions),
        total_open_quantity=sum(position.quantity for position in open_positions),
        symbols=tuple(position.symbol for position in open_positions),
        closed_trades_count=len(exit_records),
        exits_with_pnl_count=len(gross_pnl_values),
        total_simulated_gross_pnl=sum(gross_pnl_values),
        total_estimated_costs=sum(
            exit_record.total_estimated_costs for exit_record in exit_records
        ),
        total_simulated_net_pnl=sum(net_pnl_values),
        winning_exits_count=winning_exits_count,
        losing_exits_count=losing_exits_count,
        flat_exits_count=flat_exits_count,
        unknown_pnl_exits_count=unknown_pnl_exits_count,
        net_winning_exits_count=net_winning_exits_count,
        net_losing_exits_count=net_losing_exits_count,
        net_flat_exits_count=net_flat_exits_count,
        unknown_net_pnl_exits_count=unknown_net_pnl_exits_count,
    )
