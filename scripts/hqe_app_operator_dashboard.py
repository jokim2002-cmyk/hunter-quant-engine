from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

VERSION = "HQE_APP_OPERATOR_DASHBOARD_V1"

VALIDATION_MINIMUMS = {
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


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_call(
    name: str,
    callback: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    try:
        payload = callback()
        if not isinstance(payload, dict):
            raise TypeError("Snapshot did not return a dictionary.")
        return payload
    except Exception as exc:
        return {
            "status": "UNAVAILABLE",
            "message": f"{name} unavailable: {type(exc).__name__}",
        }


def csv_data_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
    except Exception:
        return 0
    if not rows:
        return 0
    return max(0, len(rows) - 1)


def validation_progress_from_sessions(
    sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    observed_days = len(sessions)
    observed_trades = 0
    valid_trade_days = 0
    no_trade_days = 0
    expiry_weeks: set[str] = set()

    for session in sessions:
        trading_date = str(session.get("trading_date", "")).strip()
        if trading_date:
            try:
                parsed = datetime.strptime(trading_date, "%Y-%m-%d").date()
                iso = parsed.isocalendar()
                expiry_weeks.add(f"{iso.year}-W{iso.week:02d}")
            except ValueError:
                pass

        day_trades = 0
        for artifact in session.get("artifacts", []):
            if str(artifact.get("category", "")) != "trade_log":
                continue
            raw_path = str(artifact.get("path", "")).strip()
            if raw_path:
                day_trades += csv_data_rows(Path(raw_path))

        observed_trades += day_trades
        if day_trades > 0:
            valid_trade_days += 1
        else:
            no_trade_days += 1

    expiry_week_count = len(expiry_weeks)
    minimums = dict(VALIDATION_MINIMUMS)

    progress = {
        "observed_days": observed_days,
        "observed_trades": observed_trades,
        "valid_trade_days": valid_trade_days,
        "no_trade_days": no_trade_days,
        "expiry_weeks": expiry_week_count,
        "minimum_days": minimums["observed_days"],
        "minimum_trades": minimums["observed_trades"],
        "minimum_expiry_weeks": minimums["expiry_weeks"],
        "days_complete": observed_days >= minimums["observed_days"],
        "trades_complete": observed_trades >= minimums["observed_trades"],
        "expiry_weeks_complete": expiry_week_count >= minimums["expiry_weeks"],
        "days_percent": min(
            100,
            round(observed_days / minimums["observed_days"] * 100),
        ),
        "trades_percent": min(
            100,
            round(observed_trades / minimums["observed_trades"] * 100),
        ),
        "expiry_weeks_percent": min(
            100,
            round(expiry_week_count / minimums["expiry_weeks"] * 100),
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


def _auth_snapshot() -> dict[str, Any]:
    from hqe_app_fyers_auth import auth_status_snapshot

    return auth_status_snapshot()


def _market_data_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_app_market_data_center import market_data_snapshot

    return market_data_snapshot(repo_root, workspace)


def _startup_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_app_daily_startup_center import daily_readiness_snapshot

    return daily_readiness_snapshot(repo_root, workspace)


def _paper_watch_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_app_paper_watch_control import session_snapshot

    return session_snapshot(repo_root, workspace)


def _daily_close_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_app_daily_close_center import daily_close_snapshot

    return daily_close_snapshot(repo_root, workspace)


def _history_snapshot(workspace: Path) -> dict[str, Any]:
    from hqe_app_session_history_center import session_history_snapshot

    return session_history_snapshot(workspace)


def _safety_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_app_safety_evidence_center import safety_snapshot

    return safety_snapshot(repo_root, workspace)


def choose_next_action(
    *,
    auth: dict[str, Any],
    market_data: dict[str, Any],
    startup: dict[str, Any],
    paper_watch: dict[str, Any],
    daily_close: dict[str, Any],
    safety: dict[str, Any],
) -> dict[str, str]:
    auth_status = str(auth.get("status", "")).upper()
    safety_status = str(safety.get("overall_status", "")).upper()
    paper_running = bool(paper_watch.get("running"))
    close_status = str(daily_close.get("overall_status", "")).upper()
    startup_status = str(startup.get("overall_status", "")).upper()

    latest_data = market_data.get("latest_data", {})
    data_rows = int(latest_data.get("rows", 0) or 0)

    if safety_status not in {"LOCKED_SAFE"}:
        return {
            "code": "REVIEW_SAFETY",
            "title": "Review Safety",
            "message": "Run the safety audit before continuing.",
            "target": "safety",
        }
    if auth_status != "READY":
        return {
            "code": "CONNECT_BROKER",
            "title": "Connect Fyers",
            "message": "Complete secure Fyers login/token readiness.",
            "target": "connect",
        }
    if data_rows <= 0:
        return {
            "code": "REFRESH_DATA",
            "title": "Refresh Market Data",
            "message": "Load fresh data-only market evidence.",
            "target": "connect",
        }
    if paper_running:
        return {
            "code": "WATCH_RUNNING",
            "title": "Paper Watch Running",
            "message": "Continue monitoring the current paper-only session.",
            "target": "watch",
        }
    if close_status == "READY_TO_CLOSE":
        return {
            "code": "CLOSE_DAY",
            "title": "Close Current Day",
            "message": "Generate the daily close report and evidence.",
            "target": "close",
        }
    if startup_status != "READY":
        return {
            "code": "PREPARE_DAY",
            "title": "Prepare Next Day",
            "message": "Complete the daily readiness checklist.",
            "target": "prepare",
        }
    return {
        "code": "START_WATCH",
        "title": "Start Paper Watch",
        "message": "Start the guarded paper-only watch session.",
        "target": "watch",
    }


def workflow_stage(
    name: str,
    status: str,
    message: str,
    target: str,
) -> dict[str, str]:
    return {
        "name": name,
        "status": status,
        "message": message,
        "target": target,
    }


def operator_dashboard_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    auth = safe_call("Fyers auth", _auth_snapshot)
    market_data = safe_call(
        "Market data",
        lambda: _market_data_snapshot(repo_root, workspace),
    )
    startup = safe_call(
        "Daily startup",
        lambda: _startup_snapshot(repo_root, workspace),
    )
    paper_watch = safe_call(
        "Paper watch",
        lambda: _paper_watch_snapshot(repo_root, workspace),
    )
    daily_close = safe_call(
        "Daily close",
        lambda: _daily_close_snapshot(repo_root, workspace),
    )
    history = safe_call(
        "Session history",
        lambda: _history_snapshot(workspace),
    )
    safety = safe_call(
        "Safety",
        lambda: _safety_snapshot(repo_root, workspace),
    )

    sessions = list(history.get("sessions", []))
    progress = validation_progress_from_sessions(sessions)
    next_action = choose_next_action(
        auth=auth,
        market_data=market_data,
        startup=startup,
        paper_watch=paper_watch,
        daily_close=daily_close,
        safety=safety,
    )

    latest_data = market_data.get("latest_data", {})
    data_status = str(latest_data.get("status", "CHECK"))
    auth_status = str(auth.get("status", "CHECK"))
    startup_status = str(startup.get("overall_status", "CHECK"))
    watch_status = str(paper_watch.get("session_status", "CHECK"))
    close_status = str(daily_close.get("overall_status", "CHECK"))
    safety_status = str(safety.get("overall_status", "CHECK"))

    workflow = [
        workflow_stage(
            "Connect",
            "READY" if auth_status == "READY" else "CHECK",
            f"Fyers: {auth_status} | Data: {data_status}",
            "connect",
        ),
        workflow_stage(
            "Prepare",
            "READY" if startup_status == "READY" else "CHECK",
            str(startup.get("display_text", startup_status)),
            "prepare",
        ),
        workflow_stage(
            "Watch",
            "RUNNING" if paper_watch.get("running") else watch_status,
            str(paper_watch.get("display_text", watch_status)),
            "watch",
        ),
        workflow_stage(
            "Close",
            close_status,
            str(daily_close.get("display_text", close_status)),
            "close",
        ),
        workflow_stage(
            "Review",
            "READY" if sessions else "WAITING",
            str(history.get("display_text", "No session history yet.")),
            "review",
        ),
    ]

    overall = (
        "SAFE"
        if safety_status == "LOCKED_SAFE"
        else "CHECK_REQUIRED"
    )
    display = (
        f"Operator dashboard: {overall} | "
        f"Next: {next_action['title']} | "
        f"Days {progress['observed_days']}/{progress['minimum_days']} | "
        f"Trades {progress['observed_trades']}/{progress['minimum_trades']} | "
        f"Weeks {progress['expiry_weeks']}/"
        f"{progress['minimum_expiry_weeks']}"
    )

    return {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "overall_status": overall,
        "display_text": display,
        "next_action": next_action,
        "workflow": workflow,
        "validation_progress": progress,
        "auth": auth,
        "market_data": market_data,
        "startup": startup,
        "paper_watch": paper_watch,
        "daily_close": daily_close,
        "history": history,
        "safety": safety,
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
        "workflow": "CONSOLIDATED_OPERATOR_DASHBOARD",
        "read_only_aggregation": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE consolidated operator dashboard"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
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
            operator_dashboard_snapshot(
                Path(args.repo_root),
                Path(args.workspace),
            ),
            indent=2,
            sort_keys=True,
        ))
        return 0
    parser.error("Use --guard-check or --snapshot.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
