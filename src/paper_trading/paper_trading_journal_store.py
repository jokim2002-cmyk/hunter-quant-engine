"""
Paper Trading Journal Store

Safe local persistence for fake/paper trading session journals.

Writes deterministic paper session files under reports/ only.
No broker code. No real orders. Not live market data. Not a profitability claim.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.paper_trading.paper_trading_report_writer import (
    paper_exit_record_to_dict,
    paper_order_record_to_dict,
    paper_position_to_dict,
)
from src.paper_trading.paper_trading_session_summary import (
    build_paper_trading_session_summary,
)
from src.paper_trading.paper_trading_session_summary_export import (
    paper_trading_session_summary_to_dict,
)


@dataclass(frozen=True)
class PaperTradingJournalRunPaths:
    """
    Files written for one local fake/paper journal run.
    """

    output_dir: Path
    metadata_json: Path
    summary_json: Path
    orders_json: Path
    open_positions_json: Path
    exit_records_json: Path
    manifest_json: Path


def build_paper_trading_journal_run_id(generated_at: datetime | None = None) -> str:
    """
    Build a deterministic UTC run id for a local fake/paper journal run.
    """
    timestamp = _normalize_generated_at(generated_at)
    return timestamp.strftime("%Y%m%dT%H%M%SZ")


def write_paper_trading_journal_run(
    session,
    output_dir: str | Path = Path("reports") / "paper_trading" / "journal",
    *,
    run_id: str | None = None,
    generated_at: datetime | None = None,
) -> PaperTradingJournalRunPaths:
    """
    Persist one fake/paper session journal run under reports/.

    The helper writes metadata, summary, orders, open positions, exit records,
    and a manifest. It never places orders and never connects to a broker.
    """
    timestamp = _normalize_generated_at(generated_at)
    safe_run_id = _sanitize_run_id(run_id or build_paper_trading_journal_run_id(timestamp))
    base_dir = _ensure_reports_output_dir(output_dir)
    run_dir = base_dir / safe_run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    paths = PaperTradingJournalRunPaths(
        output_dir=run_dir,
        metadata_json=run_dir / "metadata.json",
        summary_json=run_dir / "summary.json",
        orders_json=run_dir / "orders.json",
        open_positions_json=run_dir / "open_positions.json",
        exit_records_json=run_dir / "exit_records.json",
        manifest_json=run_dir / "manifest.json",
    )

    metadata = _build_metadata(run_id=safe_run_id, generated_at=timestamp)
    summary = build_paper_trading_session_summary(session)

    _write_json(paths.metadata_json, metadata)
    _write_json(
        paths.summary_json,
        {
            **metadata,
            **paper_trading_session_summary_to_dict(summary),
        },
    )
    _write_json(
        paths.orders_json,
        [paper_order_record_to_dict(order) for order in session.list_orders()],
    )
    _write_json(
        paths.open_positions_json,
        [
            paper_position_to_dict(position)
            for position in session.list_open_positions()
        ],
    )
    _write_json(
        paths.exit_records_json,
        [
            paper_exit_record_to_dict(exit_record)
            for exit_record in session.list_exit_records()
        ],
    )
    _write_json(paths.manifest_json, paper_trading_journal_manifest_to_dict(paths, metadata))

    return paths


def paper_trading_journal_manifest_to_dict(
    paths: PaperTradingJournalRunPaths,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a manifest payload for a local fake/paper journal run.
    """
    return {
        **metadata,
        "output_dir": str(paths.output_dir),
        "files": {
            "metadata_json": str(paths.metadata_json),
            "summary_json": str(paths.summary_json),
            "orders_json": str(paths.orders_json),
            "open_positions_json": str(paths.open_positions_json),
            "exit_records_json": str(paths.exit_records_json),
            "manifest_json": str(paths.manifest_json),
        },
    }


def _build_metadata(run_id: str, generated_at: datetime) -> dict[str, Any]:
    return {
        "journal_version": 1,
        "journal_source": "paper",
        "run_id": run_id,
        "generated_at": generated_at.isoformat(),
        "paper_journal_is_local_only": True,
        "paper_pnl_is_simulation_only": True,
    }


def _normalize_generated_at(generated_at: datetime | None) -> datetime:
    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    if "reports" not in [part.lower() for part in path.parts]:
        raise ValueError("paper trading journals must be written under reports/")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sanitize_run_id(run_id: str) -> str:
    value = run_id.strip()
    if not value:
        raise ValueError("paper trading journal run_id is required")

    sanitized = "".join(
        char if char.isalnum() or char in "-_." else "-"
        for char in value
    )

    if sanitized in {".", ".."}:
        raise ValueError("paper trading journal run_id is invalid")

    return sanitized


def _write_json(output_path: Path, payload: Any) -> Path:
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path
