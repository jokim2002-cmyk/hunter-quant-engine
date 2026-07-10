from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_DAILY_OPERATIONS_V2"
STATUS_NAME = "HQE_APP_DAILY_OPERATION_STATUS.json"
DAY_RE = re.compile(r"DAY[_ -]?0*(\d{1,4})", re.I)
DATE_RE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")

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

OPERATIONS = {
    "prepare_next_market_day": (
        "hqe_next_market_day_startup_pack.py", "Prepare Next Market Day", "next"
    ),
    "run_day_rollover_guard": (
        "hqe_validation_day_auto_rollover_plan.py", "Run Day Rollover Guard", "next"
    ),
    "generate_daily_close_report": (
        "hqe_daily_close_auto_report_pack.py", "Generate Daily Close Report", "latest"
    ),
}

PLAN_WORDS = ("NEXT_MARKET_DAY", "AUTO_ROLLOVER", "ROLLOVER_PLAN", "STARTUP_PACK")
OBSERVED_WORDS = (
    "PERSISTENT_PAPER_WATCH", "FORWARD_TRADE_LOG", "MARKET_CLOSE", "DAILY_CLOSE",
    "CANDLE", "SESSION", "DAY_LEDGER", "MASTER_LEDGER",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def parse_day(path: Path, payload: dict[str, Any]) -> int | None:
    for key in ("day_number", "validation_day", "observed_day_number", "next_day_number"):
        try:
            value = int(str(payload.get(key, "")).strip())
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    match = DAY_RE.search(str(path))
    return int(match.group(1)) if match else None


def parse_date(path: Path, payload: dict[str, Any]) -> str | None:
    for key in (
        "trading_date", "session_date", "market_date", "official_trading_date",
        "next_trading_date", "date",
    ):
        raw = str(payload.get(key, "")).strip()
        if raw:
            for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y_%m_%d"):
                try:
                    return datetime.strptime(raw[:10], fmt).date().isoformat()
                except ValueError:
                    pass
    match = DATE_RE.search(str(path))
    if not match:
        return None
    try:
        return date(*map(int, match.groups())).isoformat()
    except ValueError:
        return None


def classify(path: Path) -> str:
    upper = str(path).upper()
    if any(word in upper for word in PLAN_WORDS):
        return "planned"
    if any(word in upper for word in OBSERVED_WORDS):
        return "observed"
    return "neutral"


def discover_days(workspace: Path) -> list[dict[str, Any]]:
    workspace = Path(workspace)
    if not workspace.exists():
        return []
    found: list[dict[str, Any]] = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        payloads: list[dict[str, Any]] = []
        suffix = path.suffix.lower()
        upper = path.name.upper()
        if suffix == ".json":
            payloads = [read_json(path)]
        elif suffix == ".csv" and ("LEDGER" in upper or "DAY_" in upper or "TRADE_LOG" in upper):
            try:
                with path.open("r", newline="", encoding="utf-8-sig") as handle:
                    payloads = list(csv.DictReader(handle))[-500:]
            except Exception:
                payloads = []
        elif suffix in {".md", ".txt", ".html", ".htm"} and "DAY_" in upper:
            payloads = [{}]
        for payload in payloads:
            day_number = parse_day(path, payload)
            trading_date = parse_date(path, payload)
            if day_number is None or trading_date is None:
                continue
            found.append({
                "day_number": day_number,
                "trading_date": trading_date,
                "classification": classify(path),
                "path": str(path),
                "modified_at": path.stat().st_mtime,
            })
    unique: dict[tuple[int, str, str], dict[str, Any]] = {}
    for item in found:
        key = (item["day_number"], item["trading_date"], item["classification"])
        if key not in unique or item["modified_at"] > unique[key]["modified_at"]:
            unique[key] = item
    return sorted(
        unique.values(),
        key=lambda item: (item["trading_date"], item["day_number"], item["modified_at"]),
    )


def resolve_latest_validation_day(workspace: Path) -> dict[str, Any] | None:
    days = discover_days(workspace)
    observed = [item for item in days if item["classification"] != "planned"]
    selected = observed or days
    return selected[-1] if selected else None


def resolve_latest_prepared_day(workspace: Path) -> dict[str, Any] | None:
    planned = [item for item in discover_days(workspace) if item["classification"] == "planned"]
    return planned[-1] if planned else None


def next_market_date(value: str | None = None) -> str:
    current = date.fromisoformat(value) if value else date.today()
    candidate = current + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate.isoformat()


def resolve_next_day(workspace: Path) -> tuple[int, str]:
    latest = resolve_latest_validation_day(workspace)
    prepared = resolve_latest_prepared_day(workspace)
    if latest is None:
        if prepared:
            return int(prepared["day_number"]), str(prepared["trading_date"])
        return 1, next_market_date()
    expected = (
        int(latest["day_number"]) + 1,
        next_market_date(str(latest["trading_date"])),
    )
    if prepared:
        ready = (int(prepared["day_number"]), str(prepared["trading_date"]))
        if ready >= expected:
            return ready
    return expected


def ranked_files(workspace: Path, evidence_only: bool) -> list[Path]:
    latest = resolve_latest_validation_day(workspace)
    latest_day = int(latest["day_number"]) if latest else None
    latest_date = str(latest["trading_date"]) if latest else None
    ranked: list[tuple[int, float, Path]] = []
    for path in Path(workspace).rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".html", ".htm", ".pdf", ".json", ".md", ".txt", ".csv"
        }:
            continue
        upper = path.name.upper()
        full = str(path).upper()
        if evidence_only and not (
            "EVIDENCE" in upper or "MARKET_CLOSE" in full or "DAILY_CLOSE" in full
        ):
            continue
        score = 0
        if "REPORT" in upper:
            score += 130
        if "MARKET_CLOSE" in full or "DAILY_CLOSE" in full:
            score += 100
        if "EVIDENCE" in upper:
            score += 80 if evidence_only else 20
        if path.suffix.lower() in {".html", ".htm", ".pdf"}:
            score += 70
        elif path.suffix.lower() == ".json":
            score += 35 if evidence_only else 5
        if "MODULE_" in upper and "_STATUS" in upper:
            score -= 70
        payload = read_json(path) if path.suffix.lower() == ".json" else {}
        if latest_day is not None and parse_day(path, payload) == latest_day:
            score += 100
        if latest_date is not None and parse_date(path, payload) == latest_date:
            score += 100
        if score > 0:
            ranked.append((score, path.stat().st_mtime, path))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked]


def resolve_latest_report(workspace: Path) -> Path | None:
    items = ranked_files(workspace, False)
    return items[0] if items else None


def resolve_latest_evidence(workspace: Path) -> Path | None:
    items = ranked_files(workspace, True)
    return items[0] if items else None


def status_path(workspace: Path) -> Path:
    return Path(workspace) / STATUS_NAME


def read_status(workspace: Path) -> dict[str, Any]:
    return read_json(status_path(workspace))


def python_exe(repo: Path, hidden: bool) -> Path:
    scripts = Path(repo) / ".venv" / "Scripts"
    if hidden and (scripts / "pythonw.exe").exists():
        return scripts / "pythonw.exe"
    return scripts / "python.exe"


def build_guard_command(repo: Path, script: str) -> list[str]:
    return [str(python_exe(repo, False)), str(Path(repo) / "scripts" / script), "--guard-check"]


def build_action_command(
    repo: Path, workspace: Path, script: str, trading_date: str,
    day_number: int, user_id: str, symbol: str,
) -> list[str]:
    return [
        str(python_exe(repo, False)), str(Path(repo) / "scripts" / script),
        "--workspace", str(workspace), "--trading-date", trading_date,
        "--day-number", str(day_number), "--user-id", user_id,
        "--symbol", symbol, "--write",
    ]


def extract_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def validate_guard(payload: dict[str, Any]) -> None:
    if payload.get("guard_check_status") != "PASS":
        raise RuntimeError("Safety guard did not return PASS.")
    safety = payload.get("safety_lock") if isinstance(payload.get("safety_lock"), dict) else payload
    for key in ("real_money_enabled", "real_orders_enabled", "broker_execution_enabled", "auto_trading_enabled"):
        if payload.get(key) is True or safety.get(key) is True:
            raise RuntimeError(f"Forbidden safety state: {key}=true")


def run_checked(command: list[str], repo: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {detail[-1400:]}")
    return result


def operation_context(workspace: Path, operation: str) -> tuple[int, str]:
    if OPERATIONS[operation][2] == "next":
        return resolve_next_day(workspace)
    latest = resolve_latest_validation_day(workspace)
    if latest is None:
        raise RuntimeError("No observed validation day detected; daily close stopped safely.")
    return int(latest["day_number"]), str(latest["trading_date"])


def execute_operation(repo: Path, workspace: Path, operation: str, user_id: str, symbol: str) -> dict[str, Any]:
    script, label, _ = OPERATIONS[operation]
    day_number, trading_date = operation_context(workspace, operation)
    base = {
        "version": VERSION, "operation": operation, "operation_label": label,
        "status": "RUNNING", "started_at_utc": now_utc(), "pid": os.getpid(),
        "day_number": day_number, "trading_date": trading_date,
        "safety_lock": SAFETY_LOCK,
    }
    write_json(status_path(workspace), base)
    try:
        if not (Path(repo) / "scripts" / script).exists():
            raise RuntimeError(f"Required operation script missing: {script}")
        guard = run_checked(build_guard_command(repo, script), repo, 120)
        validate_guard(extract_json(guard.stdout))
        action = run_checked(
            build_action_command(repo, workspace, script, trading_date, day_number, user_id, symbol),
            repo, 300,
        )
        result = {
            **base, "status": "PASS", "finished_at_utc": now_utc(),
            "guard_check_status": "PASS", "action_payload": extract_json(action.stdout),
            "message": f"{label} completed safely.",
        }
    except Exception as exc:
        result = {
            **base, "status": "FAILED", "finished_at_utc": now_utc(),
            "message": str(exc),
        }
    write_json(status_path(workspace), result)
    return result


def launch_operation_worker(repo: Path, workspace: Path, operation: str, user_id: str, symbol: str) -> dict[str, Any]:
    if operation not in OPERATIONS:
        raise ValueError(f"Unknown operation: {operation}")
    current = read_status(workspace)
    if current.get("status") == "RUNNING":
        return {"started": False, "status": "ALREADY_RUNNING", "message": "Another daily operation is already running."}
    command = [
        str(python_exe(repo, True)), str(Path(__file__).resolve()),
        "--execute-operation", operation, "--repo-root", str(repo),
        "--workspace", str(workspace), "--user-id", user_id, "--symbol", symbol,
    ]
    kwargs: dict[str, Any] = {"cwd": str(repo), "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs["startupinfo"] = startup
    process = subprocess.Popen(command, **kwargs)
    return {"started": True, "status": "STARTED_HIDDEN", "pid": process.pid, "message": f"{OPERATIONS[operation][1]} started safely."}


def operations_snapshot(workspace: Path) -> dict[str, Any]:
    latest = resolve_latest_validation_day(workspace)
    next_day, next_date = resolve_next_day(workspace)
    report = resolve_latest_report(workspace)
    evidence = resolve_latest_evidence(workspace)
    operation = read_status(workspace)
    return {
        "version": VERSION,
        "latest_day_number": latest["day_number"] if latest else None,
        "latest_trading_date": latest["trading_date"] if latest else None,
        "next_day_number": next_day, "next_trading_date": next_date,
        "latest_report": str(report or ""), "latest_evidence": str(evidence or ""),
        "operation_status": operation.get("status", "IDLE"),
        "operation_message": operation.get("message", ""),
        "safety_lock": SAFETY_LOCK,
        "real_money_enabled": False, "real_orders_enabled": False,
        "broker_execution_enabled": False, "auto_trading_enabled": False,
        "fake_trades_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App daily operations helper")
    parser.add_argument("--execute-operation", choices=sorted(OPERATIONS))
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--user-id", default="jokim-local")
    parser.add_argument("--symbol", default="NSE:NIFTY50-INDEX")
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace)
    if args.snapshot:
        print(json.dumps(operations_snapshot(workspace), indent=2, sort_keys=True))
        return 0
    if args.execute_operation:
        repo = Path(args.repo_root) if args.repo_root.strip() else Path(__file__).resolve().parents[1]
        result = execute_operation(repo, workspace, args.execute_operation, args.user_id, args.symbol)
        return 0 if result["status"] == "PASS" else 1
    parser.error("Use --snapshot or --execute-operation.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
