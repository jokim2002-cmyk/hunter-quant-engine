from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_SESSION_HISTORY_CENTER_V1"

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

DAY_PATTERN = re.compile(r"DAY[_ -]?(\d{1,4})", re.IGNORECASE)
DATE_PATTERNS = (
    re.compile(r"(20\d{2})[-_](\d{2})[-_](\d{2})"),
    re.compile(r"(20\d{2})(\d{2})(\d{2})"),
)


def utc_text(timestamp: float) -> str:
    return datetime.fromtimestamp(
        timestamp,
        timezone.utc,
    ).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def extract_day_number(path: Path, workspace: Path) -> int | None:
    try:
        searchable = str(path.relative_to(workspace))
    except ValueError:
        searchable = str(path)
    match = DAY_PATTERN.search(searchable)
    return int(match.group(1)) if match else None


def extract_date_from_text(value: str) -> str:
    for pattern in DATE_PATTERNS:
        match = pattern.search(value)
        if not match:
            continue
        candidate = "-".join(match.groups())
        try:
            return datetime.strptime(candidate, "%Y-%m-%d").date().isoformat()
        except ValueError:
            continue
    return ""


def extract_trading_date(path: Path) -> str:
    date_text = extract_date_from_text(str(path))
    if date_text:
        return date_text
    if path.suffix.lower() == ".json":
        payload = read_json(path)
        for key in (
            "trading_date",
            "session_date",
            "market_date",
            "date",
        ):
            date_text = extract_date_from_text(
                str(payload.get(key, ""))
            )
            if date_text:
                return date_text
    return ""


def classify_artifact(path: Path) -> str:
    name = path.name.upper()
    suffix = path.suffix.lower()

    if "TRADE_LOG" in name or (
        suffix == ".csv" and "TRADE" in name
    ):
        return "trade_log"
    if "EVIDENCE" in name:
        return "evidence"
    if "REPORT" in name or "MARKET_CLOSE_PACK" in name:
        return "report"
    if "CHECKLIST" in name or "INSTRUCTION" in name:
        return "checklist"
    if "STATUS" in name or "DECISION" in name:
        return "status"
    if suffix == ".csv":
        return "data"
    if suffix == ".json":
        return "json"
    if suffix in {".txt", ".md"}:
        return "notes"
    return "other"


def nearest_day_folder(
    path: Path,
    workspace: Path,
    day_number: int,
) -> Path:
    expected = f"DAY_{day_number:03d}"
    for parent in (path.parent, *path.parents):
        if parent == workspace.parent:
            break
        normalized = parent.name.upper().replace("-", "_").replace(" ", "_")
        if expected in normalized or DAY_PATTERN.search(parent.name):
            return parent
        if parent == workspace:
            break
    return path.parent


def discover_session_history(
    workspace: Path,
    *,
    max_files: int = 10000,
) -> list[dict[str, Any]]:
    if not workspace.exists():
        return []

    grouped: dict[int, dict[str, Any]] = {}
    scanned = 0

    for path in workspace.rglob("*"):
        if scanned >= max_files:
            break
        if not path.is_file():
            continue
        scanned += 1

        day_number = extract_day_number(path, workspace)
        if day_number is None:
            continue

        stat = path.stat()
        artifact = {
            "name": path.name,
            "path": str(path),
            "category": classify_artifact(path),
            "trading_date": extract_trading_date(path),
            "updated_at_utc": utc_text(stat.st_mtime),
            "size_bytes": stat.st_size,
        }

        record = grouped.setdefault(
            day_number,
            {
                "day_number": day_number,
                "day_label": f"DAY_{day_number:03d}",
                "trading_date": "",
                "latest_updated_utc": "",
                "latest_updated_timestamp": 0.0,
                "day_folder": "",
                "artifact_count": 0,
                "category_counts": {},
                "artifacts": [],
            },
        )

        record["artifacts"].append(artifact)
        record["artifact_count"] += 1

        category = artifact["category"]
        category_counts = record["category_counts"]
        category_counts[category] = category_counts.get(category, 0) + 1

        if artifact["trading_date"] and not record["trading_date"]:
            record["trading_date"] = artifact["trading_date"]

        if stat.st_mtime >= record["latest_updated_timestamp"]:
            record["latest_updated_timestamp"] = stat.st_mtime
            record["latest_updated_utc"] = artifact["updated_at_utc"]
            record["day_folder"] = str(
                nearest_day_folder(path, workspace, day_number)
            )

    sessions = list(grouped.values())
    for record in sessions:
        record["artifacts"].sort(
            key=lambda artifact: (
                artifact["category"],
                artifact["name"].lower(),
            )
        )
        record.pop("latest_updated_timestamp", None)

    sessions.sort(key=lambda record: record["day_number"], reverse=True)
    return sessions


def filter_sessions(
    sessions: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    needle = query.strip().lower()
    if not needle:
        return list(sessions)

    filtered: list[dict[str, Any]] = []
    for session in sessions:
        searchable = [
            str(session.get("day_label", "")),
            str(session.get("day_number", "")),
            str(session.get("trading_date", "")),
        ]
        for artifact in session.get("artifacts", []):
            searchable.extend(
                (
                    str(artifact.get("name", "")),
                    str(artifact.get("category", "")),
                    str(artifact.get("path", "")),
                )
            )
        if needle in " ".join(searchable).lower():
            filtered.append(session)
    return filtered


def session_history_snapshot(workspace: Path) -> dict[str, Any]:
    sessions = discover_session_history(workspace)
    total_artifacts = sum(
        int(session.get("artifact_count", 0))
        for session in sessions
    )
    latest = sessions[0] if sessions else {}
    display = (
        f"Session history: {len(sessions)} days | "
        f"Artifacts: {total_artifacts} | "
        f"Latest: {latest.get('day_label', 'none')}"
    )
    return {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "workspace": str(workspace),
        "workspace_ready": workspace.exists(),
        "session_count": len(sessions),
        "artifact_count": total_artifacts,
        "latest_day_number": int(latest.get("day_number", 0) or 0),
        "latest_day_label": str(latest.get("day_label", "")),
        "sessions": sessions,
        "display_text": display,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "SESSION_HISTORY_AND_EVIDENCE_BROWSER",
        "read_only_browser": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app session history and evidence browser"
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")
    if args.snapshot:
        print(json.dumps(
            session_history_snapshot(Path(args.workspace)),
            indent=2,
            sort_keys=True,
        ))
        return 0
    parser.error("Use --guard-check or --snapshot.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
