"""
Paper Trading Report Writer

Writes fake/local paper trading reports under reports/ only.
No real orders. No broker code. No external SDK. Not live market data.
Not a profitability claim.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.paper_trading.paper_order_journal import PaperOrderRecord
from src.paper_trading.paper_position_state import PaperPosition
from src.paper_trading.paper_realized_exit_record import PaperRealizedExitRecord
from src.paper_trading.paper_trading_session_summary import (
    PaperTradingSessionSummary,
    build_paper_trading_session_summary,
)
from src.paper_trading.paper_trading_session_summary_export import (
    format_paper_trading_session_summary,
    paper_trading_session_summary_to_csv_row,
    paper_trading_session_summary_to_dict,
)


PaperTradingReportSummary = PaperTradingSessionSummary


@dataclass(frozen=True)
class PaperTradingReportPaths:
    """
    Paths written by the local paper trading report writer.
    """

    output_dir: Path
    summary_json: Path
    summary_csv: Path
    orders_json: Path
    orders_csv: Path
    open_positions_json: Path
    open_positions_csv: Path
    exit_records_json: Path
    exit_records_csv: Path
    report_text: Path


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    """
    Validate and create an output directory under reports/.
    """
    path = Path(output_dir)
    if "reports" not in [part.lower() for part in path.parts]:
        raise ValueError("paper trading reports must be written under reports/")

    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(output_path: Path, payload: Any) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value


def _write_csv(
    output_path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {fieldname: _csv_value(row.get(fieldname)) for fieldname in fieldnames}
            )

    return output_path


def paper_order_record_to_dict(record: PaperOrderRecord) -> dict[str, Any]:
    """
    Convert a fake paper order record to a serializable dictionary.
    """
    return {
        "order_id": record.order_id,
        "symbol": record.symbol,
        "quantity": record.quantity,
        "planned_entry_price": record.planned_entry_price,
        "status": record.status.value,
        "created_at": record.created_at.isoformat(),
        "source": record.source,
        "plan_id": record.plan_id,
    }


def paper_position_to_dict(position: PaperPosition) -> dict[str, Any]:
    """
    Convert an open fake paper position to a serializable dictionary.
    """
    return {
        "symbol": position.symbol,
        "quantity": position.quantity,
        "average_entry_price": position.average_entry_price,
        "opened_at": position.opened_at.isoformat(),
        "source": position.source,
    }


def paper_exit_record_to_dict(
    exit_record: PaperRealizedExitRecord,
) -> dict[str, Any]:
    """
    Convert a local paper exit record to a serializable dictionary.
    """
    return {
        "exit_id": exit_record.exit_id,
        "symbol": exit_record.symbol,
        "quantity": exit_record.quantity,
        "average_entry_price": exit_record.average_entry_price,
        "opened_at": exit_record.opened_at.isoformat(),
        "closed_at": exit_record.closed_at.isoformat(),
        "exit_reason": exit_record.exit_reason.value,
        "exit_price": exit_record.exit_price,
        "has_exit_price": exit_record.has_exit_price,
        "simulated_points": exit_record.simulated_points,
        "simulated_gross_pnl": exit_record.simulated_gross_pnl,
        "estimated_exit_charges": exit_record.estimated_exit_charges,
        "estimated_slippage": exit_record.estimated_slippage,
        "total_estimated_costs": exit_record.total_estimated_costs,
        "simulated_net_pnl": exit_record.simulated_net_pnl,
        "source": exit_record.source,
    }


def build_paper_trading_report_summary(session) -> PaperTradingReportSummary:
    """
    Build a trader-friendly report summary from a paper trading session.
    """
    return build_paper_trading_session_summary(session)


def paper_trading_report_summary_to_dict(
    report_summary: PaperTradingReportSummary,
) -> dict[str, Any]:
    """
    Convert a paper trading report summary to a serializable dictionary.
    """
    return paper_trading_session_summary_to_dict(report_summary)


def paper_trading_report_summary_to_csv_row(
    report_summary: PaperTradingReportSummary,
) -> dict[str, Any]:
    """
    Convert report summary to a one-row CSV-friendly dictionary.
    """
    return paper_trading_session_summary_to_csv_row(report_summary)


def _format_report_text(
    summary_text: str,
    orders_count: int,
    open_positions_count: int,
    exit_records_count: int,
) -> str:
    return "\n".join(
        [
            summary_text,
            "",
            "Paper Trading Report Files",
            f"orders count: {orders_count}",
            f"open positions count: {open_positions_count}",
            f"exit records count: {exit_records_count}",
            "local report/export only",
            "no broker/fyers",
            "no live/real market data",
            "no real orders",
            "not a profitability claim",
            "",
        ]
    )


def write_paper_trading_report(
    session,
    output_dir: str | Path = Path("reports") / "paper_trading",
) -> PaperTradingReportPaths:
    """
    Write a local paper trading report bundle under reports/.

    Writes summary, orders, open positions, and exit records.
    This writer never places real orders and never calls external systems.
    """
    base_dir = _ensure_reports_output_dir(output_dir)

    report_summary = build_paper_trading_report_summary(session)
    report_summary_payload = paper_trading_report_summary_to_dict(report_summary)
    report_summary_csv_row = paper_trading_report_summary_to_csv_row(report_summary)

    orders = [paper_order_record_to_dict(record) for record in session.list_orders()]
    open_positions = [
        paper_position_to_dict(position) for position in session.list_open_positions()
    ]
    exit_records = [
        paper_exit_record_to_dict(exit_record)
        for exit_record in session.list_exit_records()
    ]

    paths = PaperTradingReportPaths(
        output_dir=base_dir,
        summary_json=base_dir / "summary.json",
        summary_csv=base_dir / "summary.csv",
        orders_json=base_dir / "orders.json",
        orders_csv=base_dir / "orders.csv",
        open_positions_json=base_dir / "open_positions.json",
        open_positions_csv=base_dir / "open_positions.csv",
        exit_records_json=base_dir / "exit_records.json",
        exit_records_csv=base_dir / "exit_records.csv",
        report_text=base_dir / "report.txt",
    )

    _write_json(paths.summary_json, report_summary_payload)
    _write_csv(
        paths.summary_csv,
        [report_summary_csv_row],
        list(report_summary_csv_row),
    )

    _write_json(paths.orders_json, orders)
    _write_csv(
        paths.orders_csv,
        orders,
        [
            "order_id",
            "symbol",
            "quantity",
            "planned_entry_price",
            "status",
            "created_at",
            "source",
            "plan_id",
        ],
    )

    _write_json(paths.open_positions_json, open_positions)
    _write_csv(
        paths.open_positions_csv,
        open_positions,
        [
            "symbol",
            "quantity",
            "average_entry_price",
            "opened_at",
            "source",
        ],
    )

    _write_json(paths.exit_records_json, exit_records)
    _write_csv(
        paths.exit_records_csv,
        exit_records,
        [
            "exit_id",
            "symbol",
            "quantity",
            "average_entry_price",
            "opened_at",
            "closed_at",
            "exit_reason",
            "exit_price",
            "has_exit_price",
            "simulated_points",
            "simulated_gross_pnl",
            "estimated_exit_charges",
            "estimated_slippage",
            "total_estimated_costs",
            "simulated_net_pnl",
            "source",
        ],
    )

    summary_text = format_paper_trading_session_summary(report_summary)
    paths.report_text.write_text(
        _format_report_text(
            summary_text=summary_text,
            orders_count=len(orders),
            open_positions_count=len(open_positions),
            exit_records_count=len(exit_records),
        ),
        encoding="utf-8",
    )

    return paths
