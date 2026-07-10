from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import zipfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VERSION = "HQE_PAPER_VALIDATION_REPORT_ENGINE_V1"
STATUS_FILE = "HQE_PAPER_VALIDATION_REPORT_STATUS.json"
REPORT_ROOT = "HQE_PAPER_VALIDATION_REPORTS"

MINIMUMS = {
    "observed_days": 20,
    "observed_trades": 30,
    "expiry_weeks": 4,
}

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}

NO_TRADE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "SIDEWAYS_OR_LOW_EFFICIENCY",
        (
            "sideways",
            "low efficiency",
            "efficiency ratio",
            "er20",
            "range compression",
            "compressed range",
        ),
    ),
    (
        "NO_VALID_SIGNAL",
        (
            "no signal",
            "no valid signal",
            "signal not found",
            "conditions not met",
            "entry not triggered",
        ),
    ),
    (
        "OPTION_FILTER_REJECTED",
        (
            "dte",
            "ltp range",
            "option ltp",
            "estimated net reward",
            "reward filter",
            "option filter",
        ),
    ),
    (
        "DATA_QUALITY_OR_MISSING_DATA",
        (
            "missing data",
            "data gap",
            "invalid candle",
            "duplicate candle",
            "stale data",
            "no market data",
            "quality failed",
        ),
    ),
    (
        "BROKER_AUTH_OR_TOKEN",
        (
            "token expired",
            "auth failed",
            "login required",
            "fyers token",
            "access token",
            "broker auth",
        ),
    ),
    (
        "MARKET_CLOSED_OR_HOLIDAY",
        (
            "market closed",
            "holiday",
            "weekend",
            "non trading day",
            "non-trading day",
        ),
    ),
    (
        "SAFETY_OR_KILL_SWITCH",
        (
            "kill switch",
            "safety block",
            "blocked safely",
            "guard failed",
            "guard check failed",
        ),
    ),
)


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def csv_data_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            row_count = sum(1 for _ in reader)
    except Exception:
        return 0
    return max(0, row_count - 1)


def flatten_json_text(value: Any) -> list[str]:
    output: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            output.append(str(key))
            output.extend(flatten_json_text(item))
    elif isinstance(value, list):
        for item in value:
            output.extend(flatten_json_text(item))
    elif value is not None:
        output.append(str(value))
    return output


def artifact_text(path: Path, *, limit_bytes: int = 200_000) -> str:
    try:
        if path.stat().st_size > limit_bytes:
            return path.name
        if path.suffix.lower() == ".json":
            payload = read_json(path)
            return " ".join(flatten_json_text(payload))
        if path.suffix.lower() in {".txt", ".md", ".csv"}:
            return path.read_text(
                encoding="utf-8-sig",
                errors="ignore",
            )[:limit_bytes]
    except Exception:
        return path.name
    return path.name


def classify_no_trade_reason(text: str) -> str:
    lowered = " ".join(text.lower().split())
    for category, patterns in NO_TRADE_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            return category
    return "NO_TRADE_REASON_NOT_RECORDED"


def session_trade_count(session: dict[str, Any]) -> int:
    total = 0
    for artifact in session.get("artifacts", []):
        if str(artifact.get("category", "")) != "trade_log":
            continue
        raw_path = str(artifact.get("path", "")).strip()
        if raw_path:
            total += csv_data_rows(Path(raw_path))
    return total


def session_reason_text(session: dict[str, Any]) -> str:
    parts = [
        str(session.get("day_label", "")),
        str(session.get("trading_date", "")),
    ]
    for artifact in session.get("artifacts", []):
        raw_path = str(artifact.get("path", "")).strip()
        if not raw_path:
            continue
        path = Path(raw_path)
        parts.append(path.name)
        if path.exists():
            parts.append(artifact_text(path))
    return " ".join(parts)


def build_daily_records(
    sessions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for session in sorted(
        sessions,
        key=lambda item: int(item.get("day_number", 0) or 0),
    ):
        trades = session_trade_count(session)
        trading_date = str(session.get("trading_date", "")).strip()
        iso_week = ""
        if trading_date:
            try:
                parsed = date.fromisoformat(trading_date)
                calendar = parsed.isocalendar()
                iso_week = f"{calendar.year}-W{calendar.week:02d}"
            except ValueError:
                pass

        reason = ""
        if trades == 0:
            reason = classify_no_trade_reason(
                session_reason_text(session)
            )

        records.append(
            {
                "day_number": int(
                    session.get("day_number", 0) or 0
                ),
                "day_label": str(session.get("day_label", "")),
                "trading_date": trading_date,
                "iso_week": iso_week,
                "trade_count": trades,
                "valid_trade_day": trades > 0,
                "no_trade_reason": reason,
                "artifact_count": int(
                    session.get("artifact_count", 0) or 0
                ),
                "day_folder": str(session.get("day_folder", "")),
            }
        )
    return records


def progress_from_daily_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    observed_days = len(records)
    observed_trades = sum(
        int(record.get("trade_count", 0) or 0)
        for record in records
    )
    valid_trade_days = sum(
        1 for record in records
        if record.get("valid_trade_day") is True
    )
    no_trade_days = observed_days - valid_trade_days
    expiry_weeks = len(
        {
            str(record.get("iso_week", ""))
            for record in records
            if str(record.get("iso_week", ""))
        }
    )

    progress = {
        "observed_days": observed_days,
        "observed_trades": observed_trades,
        "valid_trade_days": valid_trade_days,
        "no_trade_days": no_trade_days,
        "expiry_weeks": expiry_weeks,
        "minimum_days": MINIMUMS["observed_days"],
        "minimum_trades": MINIMUMS["observed_trades"],
        "minimum_expiry_weeks": MINIMUMS["expiry_weeks"],
        "days_complete": observed_days >= MINIMUMS["observed_days"],
        "trades_complete": (
            observed_trades >= MINIMUMS["observed_trades"]
        ),
        "expiry_weeks_complete": (
            expiry_weeks >= MINIMUMS["expiry_weeks"]
        ),
        "days_percent": min(
            100,
            round(
                observed_days
                / MINIMUMS["observed_days"]
                * 100
            ),
        ),
        "trades_percent": min(
            100,
            round(
                observed_trades
                / MINIMUMS["observed_trades"]
                * 100
            ),
        ),
        "expiry_weeks_percent": min(
            100,
            round(
                expiry_weeks
                / MINIMUMS["expiry_weeks"]
                * 100
            ),
        ),
    }
    progress["validation_minimums_complete"] = all(
        (
            progress["days_complete"],
            progress["trades_complete"],
            progress["expiry_weeks_complete"],
        )
    )
    return progress


def weekly_summaries(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        week = str(record.get("iso_week", "")) or "UNKNOWN_WEEK"
        grouped.setdefault(week, []).append(record)

    output: list[dict[str, Any]] = []
    for week, items in sorted(grouped.items()):
        trades = sum(
            int(item.get("trade_count", 0) or 0)
            for item in items
        )
        no_trade_counter = Counter(
            str(item.get("no_trade_reason", ""))
            for item in items
            if str(item.get("no_trade_reason", ""))
        )
        output.append(
            {
                "iso_week": week,
                "observed_days": len(items),
                "trade_count": trades,
                "valid_trade_days": sum(
                    1 for item in items
                    if item.get("valid_trade_day") is True
                ),
                "no_trade_days": sum(
                    1 for item in items
                    if item.get("valid_trade_day") is not True
                ),
                "top_no_trade_reason": (
                    no_trade_counter.most_common(1)[0][0]
                    if no_trade_counter
                    else ""
                ),
            }
        )
    return output


def strategy_drift_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_strategy_builder_engine import active_selection_snapshot
    from hqe_strategy_pack_schema import validate_strategy_pack

    locked_path = (
        repo_root
        / "strategy_packs"
        / "builtin"
        / "hqe_locked_forward_candidate.json"
    )
    locked_pack = read_json(locked_path)
    locked_validation = (
        validate_strategy_pack(locked_pack)
        if locked_pack
        else {
            "valid": False,
            "fingerprint": "",
            "errors": ["Locked candidate file missing."],
        }
    )
    selection = active_selection_snapshot(workspace)

    if not selection.get("selected"):
        return {
            "status": "LOCKED_CANDIDATE_DEFAULT",
            "drift_detected": False,
            "message": (
                "No alternate active selection. Locked forward "
                "candidate remains the validation baseline."
            ),
            "locked_strategy_id": str(
                locked_pack.get("strategy_id", "")
            ),
            "locked_fingerprint": str(
                locked_validation.get("fingerprint", "")
            ),
            "selection": selection,
        }

    selected_path = Path(str(selection.get("pack_path", "")))
    selected_pack = read_json(selected_path)
    selected_validation = (
        validate_strategy_pack(selected_pack)
        if selected_pack
        else {
            "valid": False,
            "fingerprint": "",
            "errors": ["Selected pack file missing."],
        }
    )
    same_id = (
        str(selected_pack.get("strategy_id", ""))
        == str(locked_pack.get("strategy_id", ""))
    )
    selected_fingerprint = str(
        selected_validation.get("fingerprint", "")
    )
    locked_fingerprint = str(
        locked_validation.get("fingerprint", "")
    )
    same_fingerprint = bool(
        selected_fingerprint
        and selected_fingerprint == locked_fingerprint
    )
    drift = not (
        selected_validation.get("valid")
        and same_id
        and same_fingerprint
    )
    return {
        "status": "DRIFT_DETECTED" if drift else "MATCH",
        "drift_detected": drift,
        "message": (
            "Active paper strategy differs from the locked "
            "forward-validation candidate."
            if drift
            else "Active paper strategy matches the locked candidate."
        ),
        "locked_strategy_id": str(
            locked_pack.get("strategy_id", "")
        ),
        "selected_strategy_id": str(
            selected_pack.get("strategy_id", "")
        ),
        "locked_fingerprint": locked_fingerprint,
        "selected_fingerprint": selected_fingerprint,
        "selection": selection,
        "selected_validation": selected_validation,
    }


def no_trade_reason_summary(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counter = Counter(
        str(record.get("no_trade_reason", ""))
        for record in records
        if str(record.get("no_trade_reason", ""))
    )
    total = sum(counter.values())
    return [
        {
            "reason": reason,
            "count": count,
            "percent_of_no_trade_days": (
                round(count / total * 100, 2)
                if total
                else 0.0
            ),
        }
        for reason, count in counter.most_common()
    ]


def decision_status(
    *,
    progress: dict[str, Any],
    drift: dict[str, Any],
    safety: dict[str, Any],
) -> dict[str, str]:
    kill_switch = str(
        safety.get("kill_switch_status", "")
    ).upper()
    overall_safety = str(
        safety.get("overall_status", "")
    ).upper()

    if kill_switch == "TRIGGERED":
        return {
            "status": "KILL_SWITCH_TRIGGERED",
            "message": (
                "Validation is blocked because kill-switch evidence "
                "is triggered."
            ),
        }
    if drift.get("drift_detected") is True:
        return {
            "status": "DRIFT_REVIEW_REQUIRED",
            "message": (
                "Active strategy differs from the locked candidate. "
                "Review before continuing validation."
            ),
        }
    if overall_safety not in {"LOCKED_SAFE"}:
        return {
            "status": "SAFETY_REVIEW_REQUIRED",
            "message": (
                "Safety evidence is not in LOCKED_SAFE status."
            ),
        }
    if progress.get("validation_minimums_complete") is True:
        return {
            "status": "READY_FOR_FORMAL_REVIEW",
            "message": (
                "Minimum observation thresholds are complete. "
                "A formal evidence review is required; this is not "
                "a profitability claim."
            ),
        }
    return {
        "status": "HOLD_MORE_DATA_REQUIRED",
        "message": (
            "Continue paper-only observation until minimum days, "
            "trades and expiry weeks are complete."
        ),
    }


def validation_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_app_session_history_center import session_history_snapshot
    from hqe_app_safety_evidence_center import safety_snapshot

    history = session_history_snapshot(workspace)
    sessions = list(history.get("sessions", []))
    daily = build_daily_records(sessions)
    progress = progress_from_daily_records(daily)
    weekly = weekly_summaries(daily)
    no_trade = no_trade_reason_summary(daily)
    drift = strategy_drift_snapshot(repo_root, workspace)
    safety = safety_snapshot(repo_root, workspace)
    decision = decision_status(
        progress=progress,
        drift=drift,
        safety=safety,
    )

    display = (
        f"Paper validation: {decision['status']} | "
        f"Days {progress['observed_days']}/"
        f"{progress['minimum_days']} | "
        f"Trades {progress['observed_trades']}/"
        f"{progress['minimum_trades']} | "
        f"Weeks {progress['expiry_weeks']}/"
        f"{progress['minimum_expiry_weeks']} | "
        f"Drift {drift['status']}"
    )
    return {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "display_text": display,
        "decision": decision,
        "progress": progress,
        "strategy_drift": drift,
        "safety": safety,
        "daily_records": daily,
        "weekly_summaries": weekly,
        "no_trade_reasons": no_trade,
        "history": {
            "session_count": history.get("session_count", 0),
            "artifact_count": history.get("artifact_count", 0),
        },
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def render_html(snapshot: dict[str, Any]) -> str:
    progress = snapshot["progress"]
    decision = snapshot["decision"]
    drift = snapshot["strategy_drift"]
    safety = snapshot["safety"]

    def table(
        rows: list[dict[str, Any]],
        columns: list[str],
    ) -> str:
        if not rows:
            return "<p>No records available.</p>"
        header = "".join(
            f"<th>{html.escape(column)}</th>"
            for column in columns
        )
        body = "".join(
            "<tr>"
            + "".join(
                f"<td>{html.escape(str(row.get(column, '')))}</td>"
                for column in columns
            )
            + "</tr>"
            for row in rows
        )
        return (
            "<table><thead><tr>"
            + header
            + "</tr></thead><tbody>"
            + body
            + "</tbody></table>"
        )

    daily_columns = [
        "day_label",
        "trading_date",
        "iso_week",
        "trade_count",
        "valid_trade_day",
        "no_trade_reason",
    ]
    weekly_columns = [
        "iso_week",
        "observed_days",
        "trade_count",
        "valid_trade_days",
        "no_trade_days",
        "top_no_trade_reason",
    ]
    reason_columns = [
        "reason",
        "count",
        "percent_of_no_trade_days",
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HQE Paper Validation Report</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #222; }}
h1, h2 {{ margin-bottom: 8px; }}
.card {{ border: 1px solid #bbb; padding: 14px; margin: 12px 0; border-radius: 6px; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; }}
th, td {{ border: 1px solid #bbb; padding: 7px; text-align: left; }}
th {{ background: #eee; }}
.lock {{ font-weight: 600; }}
</style>
</head>
<body>
<h1>HQE Paper Validation Report</h1>
<p>Generated: {html.escape(snapshot["generated_at_utc"])}</p>
<div class="card">
<h2>Decision</h2>
<p><strong>{html.escape(decision["status"])}</strong></p>
<p>{html.escape(decision["message"])}</p>
</div>
<div class="card">
<h2>Progress</h2>
<p>Observed days: {progress["observed_days"]}/{progress["minimum_days"]}</p>
<p>Observed paper trades: {progress["observed_trades"]}/{progress["minimum_trades"]}</p>
<p>Expiry weeks: {progress["expiry_weeks"]}/{progress["minimum_expiry_weeks"]}</p>
<p>Valid trade days: {progress["valid_trade_days"]}</p>
<p>No-trade days: {progress["no_trade_days"]}</p>
</div>
<div class="card">
<h2>Strategy Drift</h2>
<p>{html.escape(drift["status"])}</p>
<p>{html.escape(drift["message"])}</p>
</div>
<div class="card">
<h2>Safety</h2>
<p>Overall: {html.escape(str(safety.get("overall_status", "")))}</p>
<p>Kill switch: {html.escape(str(safety.get("kill_switch_status", "")))}</p>
</div>
<h2>Weekly Summary</h2>
{table(snapshot["weekly_summaries"], weekly_columns)}
<h2>No-Trade Reasons</h2>
{table(snapshot["no_trade_reasons"], reason_columns)}
<h2>Daily Records</h2>
{table(snapshot["daily_records"], daily_columns)}
<p class="lock">
PAPER/DATA ONLY. REAL MONEY: NO. REAL ORDERS: NO.
BROKER EXECUTION: NO. AUTO TRADING: NO. OPTION SELLING: NO.
</p>
<p>This is not a profitability claim.</p>
</body>
</html>
"""


def generate_report_pack(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    status_path = workspace / STATUS_FILE
    write_json(
        status_path,
        {
            "version": VERSION,
            "status": "RUNNING",
            "message": "Generating paper-validation report pack.",
            "started_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        },
    )

    snapshot = validation_snapshot(repo_root, workspace)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_dir = workspace / REPORT_ROOT / f"REPORT_{stamp}"
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "HQE_PAPER_VALIDATION_REPORT.json"
    html_path = report_dir / "HQE_PAPER_VALIDATION_REPORT.html"
    daily_csv = report_dir / "HQE_PAPER_VALIDATION_DAILY_SUMMARY.csv"
    weekly_csv = report_dir / "HQE_PAPER_VALIDATION_WEEKLY_SUMMARY.csv"
    reasons_csv = report_dir / "HQE_PAPER_VALIDATION_NO_TRADE_REASONS.csv"
    zip_path = report_dir / "HQE_PAPER_VALIDATION_REPORT_PACK.zip"

    write_json(json_path, snapshot)
    html_path.write_text(render_html(snapshot), encoding="utf-8")
    write_csv(
        daily_csv,
        snapshot["daily_records"],
        [
            "day_number",
            "day_label",
            "trading_date",
            "iso_week",
            "trade_count",
            "valid_trade_day",
            "no_trade_reason",
            "artifact_count",
            "day_folder",
        ],
    )
    write_csv(
        weekly_csv,
        snapshot["weekly_summaries"],
        [
            "iso_week",
            "observed_days",
            "trade_count",
            "valid_trade_days",
            "no_trade_days",
            "top_no_trade_reason",
        ],
    )
    write_csv(
        reasons_csv,
        snapshot["no_trade_reasons"],
        [
            "reason",
            "count",
            "percent_of_no_trade_days",
        ],
    )

    files = [
        json_path,
        html_path,
        daily_csv,
        weekly_csv,
        reasons_csv,
    ]
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for path in files:
            archive.write(path, arcname=path.name)

    payload = {
        "version": VERSION,
        "status": "PASS",
        "message": (
            "Paper-validation report pack generated. "
            "This is not a profitability claim."
        ),
        "completed_at_utc": utc_now_text(),
        "decision_status": snapshot["decision"]["status"],
        "report_dir": str(report_dir),
        "json_path": str(json_path),
        "html_path": str(html_path),
        "daily_csv_path": str(daily_csv),
        "weekly_csv_path": str(weekly_csv),
        "reasons_csv_path": str(reasons_csv),
        "zip_path": str(zip_path),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }
    write_json(status_path, payload)
    return payload


def latest_report_pack(workspace: Path) -> dict[str, str]:
    root = workspace / REPORT_ROOT
    candidates = sorted(
        (
            path
            for path in root.glob("REPORT_*")
            if path.is_dir()
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if root.exists() else []
    if not candidates:
        return {
            "report_dir": "",
            "html_path": "",
            "json_path": "",
            "zip_path": "",
        }
    report_dir = candidates[0]
    return {
        "report_dir": str(report_dir),
        "html_path": str(
            report_dir / "HQE_PAPER_VALIDATION_REPORT.html"
        ),
        "json_path": str(
            report_dir / "HQE_PAPER_VALIDATION_REPORT.json"
        ),
        "zip_path": str(
            report_dir / "HQE_PAPER_VALIDATION_REPORT_PACK.zip"
        ),
    }


def report_center_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    snapshot = validation_snapshot(repo_root, workspace)
    latest = latest_report_pack(workspace)
    operation = read_json(workspace / STATUS_FILE)
    return {
        **snapshot,
        "latest_report": latest,
        "operation": operation,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "PAPER_VALIDATION_INTELLIGENCE_AND_EXPORT",
        "report_formats": ["JSON", "HTML", "CSV", "ZIP"],
        "paper_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE paper-validation report engine"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--generate-report-pack", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")

    repo_root = Path(args.repo_root)
    workspace = Path(args.workspace)

    if args.snapshot:
        print(json.dumps(
            report_center_snapshot(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.generate_report_pack:
        print(json.dumps(
            generate_report_pack(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0

    parser.error(
        "Use --snapshot, --generate-report-pack or --guard-check."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
