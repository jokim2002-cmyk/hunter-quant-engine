from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from hqe_app_daily_operations import (
    resolve_latest_evidence,
    resolve_latest_report,
)

IST = ZoneInfo("Asia/Kolkata")
DATE_PATTERN = re.compile(
    r"(?<!\d)(20\d{2})[-_/](\d{2})[-_/](\d{2})(?!\d)"
)
DAY_LABEL_PATTERN = re.compile(
    r"DAY_\d+_(20\d{2}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def ist_today(now: datetime | date | None = None) -> date:
    if now is None:
        return datetime.now(IST).date()
    if isinstance(now, datetime):
        if now.tzinfo is None:
            return now.replace(tzinfo=IST).date()
        return now.astimezone(IST).date()
    return now


def parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    match = DAY_LABEL_PATTERN.search(text)
    if match:
        try:
            return date.fromisoformat(match.group(1))
        except ValueError:
            pass

    match = DATE_PATTERN.search(text)
    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        except ValueError:
            pass

    for pattern in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text[:20].strip(), pattern).date()
        except ValueError:
            continue
    return None


def payload_date(payload: Any) -> date | None:
    if not isinstance(payload, dict):
        return None

    for key in (
        "day_label",
        "trading_date",
        "session_date",
        "market_date",
        "report_date",
        "latest_trading_date",
        "date",
        "created_at",
        "created_at_utc",
        "generated_at",
        "generated_at_utc",
        "timestamp",
    ):
        parsed = parse_date(payload.get(key))
        if parsed is not None:
            return parsed

    for key in ("session", "summary", "report", "metadata"):
        parsed = payload_date(payload.get(key))
        if parsed is not None:
            return parsed
    return None


def artifact_date(path: Path | None) -> date | None:
    if path is None or not path.exists():
        return None

    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(
                path.read_text(encoding="utf-8-sig")
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            payload = None
        parsed = payload_date(payload)
        if parsed is not None:
            return parsed

    for part in reversed(path.parts):
        parsed = parse_date(part)
        if parsed is not None:
            return parsed

    if path.suffix.lower() in {".html", ".htm", ".md", ".txt"}:
        try:
            sample = path.read_text(
                encoding="utf-8-sig",
                errors="ignore",
            )[:15000]
        except OSError:
            sample = ""
        parsed = parse_date(sample)
        if parsed is not None:
            return parsed

    return None


def pretty(value: date | None) -> str:
    return value.strftime("%d %b %Y") if value else "unknown date"


def current_day_report_status(
    workspace: Path,
    *,
    now: datetime | date | None = None,
    report_path: Path | None = None,
    evidence_path: Path | None = None,
) -> dict[str, Any]:
    today = ist_today(now)
    report = (
        report_path
        if report_path is not None
        else resolve_latest_report(workspace)
    )
    evidence = (
        evidence_path
        if evidence_path is not None
        else resolve_latest_evidence(workspace)
    )

    report_exists = bool(report is not None and report.exists())
    evidence_exists = bool(
        evidence is not None and evidence.exists()
    )
    report_day = artifact_date(report)
    evidence_day = artifact_date(evidence)

    today_ready = report_exists and report_day == today

    if today_ready:
        state = "TODAY_READY"
        message = (
            f"Today's trader report is ready for {pretty(today)}."
        )
    elif not report_exists:
        state = "TODAY_MISSING"
        message = (
            "TODAY'S SESSION DATA NOT AVAILABLE — no report exists for "
            f"{pretty(today)}. Start Paper Watch and wait for fresh "
            "current-day data."
        )
    elif report_day is None:
        state = "REPORT_DATE_UNVERIFIED"
        message = (
            "TODAY'S SESSION DATA NOT AVAILABLE — latest report date "
            "could not be verified. Historical or undated output is "
            "blocked from Today Report."
        )
    else:
        state = "STALE_REPORT_BLOCKED"
        message = (
            "TODAY'S SESSION DATA NOT AVAILABLE — latest report is from "
            f"{pretty(report_day)}. Historical report opening is blocked "
            "from the Today Report screen."
        )

    return {
        "state": state,
        "today_ready": today_ready,
        "today": today.isoformat(),
        "today_pretty": pretty(today),
        "report_path": str(report) if report is not None else "",
        "report_date": (
            report_day.isoformat() if report_day is not None else ""
        ),
        "report_date_pretty": pretty(report_day),
        "evidence_path": (
            str(evidence) if evidence is not None else ""
        ),
        "evidence_exists": evidence_exists,
        "evidence_date": (
            evidence_day.isoformat() if evidence_day is not None else ""
        ),
        "evidence_date_pretty": pretty(evidence_day),
        "message": message,
        "paper_only": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
    }
