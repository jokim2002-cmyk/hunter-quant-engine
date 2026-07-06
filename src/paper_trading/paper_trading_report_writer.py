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
from datetime import datetime, timezone
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
    paper_trading_session_summary_to_csv_row,
    paper_trading_session_summary_to_dict,
)


PAPER_TRADING_REPORT_VERSION = 1
PAPER_TRADING_REPORT_SOURCE = "paper"

PaperTradingReportSummary = PaperTradingSessionSummary


@dataclass(frozen=True)
class PaperTradingReportMetadata:
    """
    Trace metadata for a generated local paper trading report.
    """

    report_version: int
    report_source: str
    generated_at: str

    @property
    def paper_pnl_is_simulation_only(self) -> bool:
        """
        Make report safety meaning explicit in metadata too.
        """
        return True


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


def build_paper_trading_report_metadata(
    generated_at: datetime | None = None,
) -> PaperTradingReportMetadata:
    """
    Build deterministic trace metadata for a generated paper report.

    If generated_at is omitted, current UTC time is used. Passing generated_at
    keeps tests and replay-style report generation deterministic.
    """
    timestamp = generated_at if generated_at is not None else datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    return PaperTradingReportMetadata(
        report_version=PAPER_TRADING_REPORT_VERSION,
        report_source=PAPER_TRADING_REPORT_SOURCE,
        generated_at=timestamp.isoformat(),
    )


def paper_trading_report_metadata_to_dict(
    metadata: PaperTradingReportMetadata,
) -> dict[str, Any]:
    """
    Convert paper report metadata to a serializable dictionary.
    """
    return {
        "report_version": metadata.report_version,
        "report_source": metadata.report_source,
        "generated_at": metadata.generated_at,
        "paper_pnl_is_simulation_only": metadata.paper_pnl_is_simulation_only,
    }


def _with_report_metadata(
    payload: dict[str, Any],
    metadata: PaperTradingReportMetadata,
) -> dict[str, Any]:
    """
    Prefix a report payload with trace metadata fields.
    """
    metadata_payload = paper_trading_report_metadata_to_dict(metadata)
    return {**metadata_payload, **payload}


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
    metadata: PaperTradingReportMetadata,
    report_summary: PaperTradingReportSummary,
    orders_count: int,
    open_positions_count: int,
    exit_records_count: int,
) -> str:
    symbols = ", ".join(report_summary.symbols) if report_summary.symbols else "none"

    return "\n".join(
        [
            "Local Paper Trading Report",
            "==========================",
            "",
            "Report Metadata",
            "---------------",
            f"report version: {metadata.report_version}",
            f"report source: {metadata.report_source}",
            f"generated at: {metadata.generated_at}",
            f"paper pnl is simulation only: {metadata.paper_pnl_is_simulation_only}",
            "",
            "Paper Trading Session Summary",
            "-----------------------------",
            f"total orders: {report_summary.total_orders}",
            f"open positions count: {report_summary.open_positions_count}",
            f"total open quantity: {report_summary.total_open_quantity}",
            f"symbols: {symbols}",
            f"has open positions: {report_summary.has_open_positions}",
            "",
            "Paper Trading P&L Summary",
            "-------------------------",
            f"closed trades count: {report_summary.closed_trades_count}",
            f"has closed trades: {report_summary.has_closed_trades}",
            f"exits with pnl count: {report_summary.exits_with_pnl_count}",
            f"total simulated gross pnl: {report_summary.total_simulated_gross_pnl}",
            f"total estimated costs: {report_summary.total_estimated_costs}",
            f"total simulated net pnl: {report_summary.total_simulated_net_pnl}",
            f"winning exits count: {report_summary.winning_exits_count}",
            f"losing exits count: {report_summary.losing_exits_count}",
            f"flat exits count: {report_summary.flat_exits_count}",
            f"unknown pnl exits count: {report_summary.unknown_pnl_exits_count}",
            f"net winning exits count: {report_summary.net_winning_exits_count}",
            f"net losing exits count: {report_summary.net_losing_exits_count}",
            f"net flat exits count: {report_summary.net_flat_exits_count}",
            f"unknown net pnl exits count: {report_summary.unknown_net_pnl_exits_count}",
            "",
            "Paper Trading Report Files",
            "--------------------------",
            f"orders count: {orders_count}",
            f"open positions count: {open_positions_count}",
            f"exit records count: {exit_records_count}",
            "",
            "Safety Notes",
            "------------",
            "paper pnl is simulation only",
            "estimated costs are included in net pnl only",
            "gross pnl excludes costs",
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
    generated_at: datetime | None = None,
) -> PaperTradingReportPaths:
    """
    Write a local paper trading report bundle under reports/.

    Writes summary, orders, open positions, and exit records.
    This writer never places real orders and never calls external systems.
    """
    base_dir = _ensure_reports_output_dir(output_dir)

    metadata = build_paper_trading_report_metadata(generated_at)
    report_summary = build_paper_trading_report_summary(session)
    report_summary_payload = _with_report_metadata(
        paper_trading_report_summary_to_dict(report_summary),
        metadata,
    )
    report_summary_csv_row = _with_report_metadata(
        paper_trading_report_summary_to_csv_row(report_summary),
        metadata,
    )

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

    paths.report_text.write_text(
        _format_report_text(
            metadata=metadata,
            report_summary=report_summary,
            orders_count=len(orders),
            open_positions_count=len(open_positions),
            exit_records_count=len(exit_records),
        ),
        encoding="utf-8",
    )

    return paths
