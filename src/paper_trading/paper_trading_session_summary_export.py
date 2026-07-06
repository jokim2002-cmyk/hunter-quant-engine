"""
Paper trading session summary export helpers.

These helpers format and export local paper trading session summaries.
They are report/export utilities only and do not execute orders.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.paper_trading.paper_trading_session_summary import PaperTradingSessionSummary


def paper_trading_session_summary_to_dict(
    summary: PaperTradingSessionSummary,
) -> dict[str, Any]:
    """
    Convert a paper trading session summary to a serializable dictionary.
    """
    return {
        "total_orders": summary.total_orders,
        "open_positions_count": summary.open_positions_count,
        "total_open_quantity": summary.total_open_quantity,
        "symbols": list(summary.symbols),
        "has_open_positions": summary.has_open_positions,
        "closed_trades_count": summary.closed_trades_count,
        "has_closed_trades": summary.has_closed_trades,
        "exits_with_pnl_count": summary.exits_with_pnl_count,
        "total_simulated_gross_pnl": summary.total_simulated_gross_pnl,
        "total_estimated_costs": summary.total_estimated_costs,
        "total_simulated_net_pnl": summary.total_simulated_net_pnl,
        "winning_exits_count": summary.winning_exits_count,
        "losing_exits_count": summary.losing_exits_count,
        "flat_exits_count": summary.flat_exits_count,
        "unknown_pnl_exits_count": summary.unknown_pnl_exits_count,
        "net_winning_exits_count": summary.net_winning_exits_count,
        "net_losing_exits_count": summary.net_losing_exits_count,
        "net_flat_exits_count": summary.net_flat_exits_count,
        "unknown_net_pnl_exits_count": summary.unknown_net_pnl_exits_count,
        "paper_pnl_is_simulation_only": summary.paper_pnl_is_simulation_only,
        "estimated_costs_included_in_net_pnl": (
            summary.estimated_costs_included_in_net_pnl
        ),
        "gross_pnl_excludes_costs": summary.gross_pnl_excludes_costs,
    }


def paper_trading_session_summary_to_csv_row(
    summary: PaperTradingSessionSummary,
) -> dict[str, Any]:
    """
    Convert a paper trading session summary to a one-row CSV dictionary.
    """
    payload = paper_trading_session_summary_to_dict(summary)
    payload["symbols"] = "|".join(summary.symbols)
    return payload


def format_paper_trading_session_summary(
    summary: PaperTradingSessionSummary,
) -> str:
    """
    Format a paper trading session summary as beginner-friendly text.
    """
    symbols = ", ".join(summary.symbols) if summary.symbols else "none"

    return "\n".join(
        [
            "Paper Trading Session Summary",
            f"total orders: {summary.total_orders}",
            f"open positions count: {summary.open_positions_count}",
            f"total open quantity: {summary.total_open_quantity}",
            f"symbols: {symbols}",
            f"has open positions: {summary.has_open_positions}",
            "",
            "Paper Trading P&L Summary",
            f"closed trades count: {summary.closed_trades_count}",
            f"has closed trades: {summary.has_closed_trades}",
            f"exits with pnl count: {summary.exits_with_pnl_count}",
            f"total simulated gross pnl: {summary.total_simulated_gross_pnl}",
            f"total estimated costs: {summary.total_estimated_costs}",
            f"total simulated net pnl: {summary.total_simulated_net_pnl}",
            f"winning exits count: {summary.winning_exits_count}",
            f"losing exits count: {summary.losing_exits_count}",
            f"flat exits count: {summary.flat_exits_count}",
            f"unknown pnl exits count: {summary.unknown_pnl_exits_count}",
            f"net winning exits count: {summary.net_winning_exits_count}",
            f"net losing exits count: {summary.net_losing_exits_count}",
            f"net flat exits count: {summary.net_flat_exits_count}",
            f"unknown net pnl exits count: {summary.unknown_net_pnl_exits_count}",
            "paper pnl is simulation only",
            "estimated costs are included in net pnl only",
            "gross pnl excludes costs",
            "local summary/export only",
            "no broker/fyers",
            "no live/real market data",
            "no real orders",
            "not a profitability claim",
        ]
    )


def write_paper_trading_session_summary_json(
    summary: PaperTradingSessionSummary,
    output_path: str | Path,
) -> Path:
    """
    Write a paper trading session summary to a JSON file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = paper_trading_session_summary_to_dict(summary)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return path


def write_paper_trading_session_summary_csv(
    summary: PaperTradingSessionSummary,
    output_path: str | Path,
) -> Path:
    """
    Write a paper trading session summary to a one-row CSV file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    row = paper_trading_session_summary_to_csv_row(summary)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)

    return path
