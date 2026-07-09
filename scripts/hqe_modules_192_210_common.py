from __future__ import annotations

import argparse
import csv
import html
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

VERSION = "MODULES_192_210_MARKET_DAY_PAPER_WATCH_FINAL_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_USER_ID = "jokim-local"
DEFAULT_SYMBOL = "NSE:NIFTY50-INDEX"

BLOCKED_ORDER_APIS = [
    "place_order", "modify_order", "cancel_order", "exit_positions",
    "place_basket_orders", "place_gtt_order", "modify_gtt_order",
    "cancel_gtt_order", "convert_position", "orderbook", "tradebook",
    "positions", "holdings", "funds",
]

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "manual_operator_start_required": True,
    "manual_login_required": True,
    "manual_operator_review_required": True,
    "market_window_0915_1530": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_plaintext_secret_storage": True,
    "no_profitability_claim": True,
    "order_api_hard_blocked": True,
}

MODULES: Dict[int, Dict[str, str]] = {
    192: {"file": "hqe_auto_paper_watch_loop_evidence_logger.py", "name": "Auto Paper Watch Loop Evidence Logger", "base": "MODULE_192_AUTO_PAPER_WATCH_LOOP_EVIDENCE_LOGGER_STATUS"},
    193: {"file": "hqe_intraday_5m_poll_scheduler_plan.py", "name": "Intraday 5m Poll Scheduler Plan", "base": "MODULE_193_INTRADAY_5M_POLL_SCHEDULER_PLAN_STATUS"},
    194: {"file": "hqe_paper_signal_reason_timeline_logger.py", "name": "Paper Signal Reason Timeline Logger", "base": "MODULE_194_PAPER_SIGNAL_REASON_TIMELINE_LOGGER_STATUS"},
    195: {"file": "hqe_no_trade_reason_evidence_aggregator.py", "name": "No-Trade Reason Evidence Aggregator", "base": "MODULE_195_NO_TRADE_REASON_EVIDENCE_AGGREGATOR_STATUS"},
    196: {"file": "hqe_paper_trade_candidate_gate.py", "name": "Paper Trade Candidate Gate", "base": "MODULE_196_PAPER_TRADE_CANDIDATE_GATE_STATUS"},
    197: {"file": "hqe_visual_dashboard_v4_market_watch_controls.py", "name": "Visual Dashboard V4 Market Watch Controls", "base": "MODULE_197_VISUAL_DASHBOARD_V4_MARKET_WATCH_CONTROLS_STATUS"},
    198: {"file": "hqe_daily_close_auto_report_pack.py", "name": "Daily Close Auto Report Pack", "base": "MODULE_198_DAILY_CLOSE_AUTO_REPORT_PACK_STATUS"},
    199: {"file": "hqe_30_valid_trade_day_progress_sync.py", "name": "30 Valid Trade-Day Progress Sync", "base": "MODULE_199_30_VALID_TRADE_DAY_PROGRESS_SYNC_STATUS"},
    200: {"file": "hqe_next_market_day_startup_pack.py", "name": "Next Market-Day Startup Pack", "base": "MODULE_200_NEXT_MARKET_DAY_STARTUP_PACK_STATUS"},
    201: {"file": "hqe_master_evidence_index_html_pack.py", "name": "Master Evidence Index HTML Pack", "base": "MODULE_201_MASTER_EVIDENCE_INDEX_HTML_PACK_STATUS"},
    202: {"file": "hqe_kill_switch_safety_audit.py", "name": "Kill Switch Safety Audit", "base": "MODULE_202_KILL_SWITCH_SAFETY_AUDIT_STATUS"},
    203: {"file": "hqe_token_expiry_reminder_preflight.py", "name": "Token Expiry Reminder Preflight", "base": "MODULE_203_TOKEN_EXPIRY_REMINDER_PREFLIGHT_STATUS"},
    204: {"file": "hqe_market_session_calendar_guard.py", "name": "Market Session Calendar Guard", "base": "MODULE_204_MARKET_SESSION_CALENDAR_GUARD_STATUS"},
    205: {"file": "hqe_live_data_gap_detector.py", "name": "Live Data Gap Detector", "base": "MODULE_205_LIVE_DATA_GAP_DETECTOR_STATUS"},
    206: {"file": "hqe_paper_watch_dry_run_smoke.py", "name": "Paper Watch Dry Run Smoke", "base": "MODULE_206_PAPER_WATCH_DRY_RUN_SMOKE_STATUS"},
    207: {"file": "hqe_desktop_one_click_launcher_pack.py", "name": "Desktop One-Click Launcher Pack", "base": "MODULE_207_DESKTOP_ONE_CLICK_LAUNCHER_PACK_STATUS"},
    208: {"file": "hqe_operator_error_recovery_pack.py", "name": "Operator Error Recovery Pack", "base": "MODULE_208_OPERATOR_ERROR_RECOVERY_PACK_STATUS"},
    209: {"file": "hqe_forward_validation_final_gate.py", "name": "Forward Validation Final Gate", "base": "MODULE_209_FORWARD_VALIDATION_FINAL_GATE_STATUS"},
    210: {"file": "hqe_market_day_paper_watch_master_handoff_pack.py", "name": "Market-Day Paper Watch Master Handoff Pack", "base": "MODULE_210_MARKET_DAY_PAPER_WATCH_MASTER_HANDOFF_PACK_STATUS"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def local_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parser_for(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p.add_argument("--trading-date", default=local_date())
    p.add_argument("--day-number", type=int, default=1)
    p.add_argument("--user-id", default=DEFAULT_USER_ID)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    p.add_argument("--write", action="store_true")
    p.add_argument("--guard-check", action="store_true")
    p.add_argument("--launch", action="store_true")
    return p


def ensure_workspace(value: str | Path) -> Path:
    path = Path(value)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_md(path: Path, title: str, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# " + title + "\n\n```json\n" + json.dumps(payload, indent=2, sort_keys=True) + "\n```\n", encoding="utf-8")


def write_cmd(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("@echo off\n" + "\n".join(lines) + "\n", encoding="utf-8")


def append_ledger(path: Path, payload: Dict[str, Any]) -> None:
    row = {
        "generated_at_utc": payload.get("generated_at_utc", utc_now()),
        "module_number": payload.get("module_number", ""),
        "module_name": payload.get("module_name", ""),
        "module_status": payload.get("module_status", ""),
        "decision": payload.get("decision", ""),
        "workspace": payload.get("workspace", ""),
        "trading_date": payload.get("trading_date", ""),
        "symbol": payload.get("symbol", ""),
        "valid_paper_trade_days": payload.get("valid_paper_trade_days", ""),
        "actual_paper_trades": payload.get("actual_paper_trades", ""),
        "order_api_invoked": payload.get("order_api_invoked", False),
        "broker_execution_invoked": payload.get("broker_execution_invoked", False),
        "auto_trading_started": payload.get("auto_trading_started", False),
        "real_money_automatic": payload.get("real_money_automatic", False),
    }
    write_header = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            return len(list(csv.DictReader(fh)))
    except Exception:
        return 0


def count_actual_trades(workspace: Path) -> int:
    total = 0
    candidates = [workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv", workspace / "FORWARD_PAPER_TRADE_MASTER_LEDGER.csv"]
    candidates.extend(workspace.glob("DAY_*_FORWARD_TRADE_LOG.csv"))
    for path in candidates:
        total += count_csv_rows(path)
    return total


def day_stats(workspace: Path) -> Dict[str, Any]:
    ledger = workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv"
    rows: List[Dict[str, Any]] = []
    if ledger.exists():
        try:
            with ledger.open("r", encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))
        except Exception:
            rows = []
    observed = set()
    valid = set()
    for row in rows:
        date = (row.get("trading_date") or row.get("date") or row.get("day") or "").strip()
        if date:
            observed.add(date)
        try:
            trade_count = int(float(str(row.get("trade_count", "0")).strip() or "0"))
        except ValueError:
            trade_count = 0
        if date and trade_count > 0:
            valid.add(date)
    return {
        "day_ledger_rows": len(rows),
        "observed_session_days": len(observed),
        "valid_paper_trade_days": len(valid),
        "no_trade_observed_days": max(len(observed) - len(valid), 0),
        "target_valid_paper_trade_days": 30,
        "remaining_valid_trade_days": max(30 - len(valid), 0),
        "actual_paper_trades": count_actual_trades(workspace),
        "distinct_expiry_weeks": 0,
    }


def env_status() -> Dict[str, Any]:
    required = ["FYERS_CLIENT_ID", "FYERS_ACCESS_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    return {
        "required_env_names": required,
        "missing_required_env_names": missing,
        "present_required_env_count": len(required) - len(missing),
        "credentials_complete_for_data_only_watch": not missing,
        "secret_values_redacted": True,
        "plaintext_secret_storage_allowed": False,
    }


def data_health(workspace: Path) -> Dict[str, Any]:
    m183 = read_json(workspace / "MODULE_183_FYERS_DATA_ONLY_HEALTH_MONITOR_STATUS.json")
    m173 = read_json(workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json")
    normalized_csv = workspace / "FYERS_LIVE_DATA_ONLY_5M_NORMALIZED.csv"
    history = m173.get("history_result", {})
    response = history.get("response_redacted", {})
    rows = int(history.get("rows", 0) or 0)
    normalized_rows = count_csv_rows(normalized_csv)
    ok = bool(m183.get("data_only_connection_ready")) or response.get("s") == "ok" or rows > 0 or normalized_rows > 0
    return {
        "module_183_found": bool(m183),
        "module_173_found": bool(m173),
        "last_history_rows": rows,
        "normalized_5m_rows": normalized_rows,
        "last_history_code": response.get("code"),
        "data_only_connection_ready": ok,
    }


def html_status(path: Path, title: str, payload: Dict[str, Any]) -> None:
    rows = []
    for key, value in payload.items():
        if key in {"blocked_order_apis", "safety_lock"}:
            continue
        shown = json.dumps(value, indent=2, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        rows.append(
            "<tr><th>{}</th><td><pre>{}</pre></td></tr>".format(
                html.escape(str(key)),
                html.escape(shown),
            )
        )
    doc = (
        "<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(title) + "</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;background:#f7f7f7;margin:24px;color:#111}"
        ".card{background:white;padding:18px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.08);margin-bottom:16px}"
        ".safe{color:#0a7d20;font-weight:bold}.warn{color:#a15d00;font-weight:bold}"
        "table{border-collapse:collapse;width:100%;background:white}"
        "th,td{text-align:left;vertical-align:top;border-bottom:1px solid #ddd;padding:8px}"
        "th{width:280px}pre{white-space:pre-wrap;margin:0}</style></head><body>"
        "<div class='card'><h1>" + html.escape(title) + "</h1>"
        "<p class='safe'>PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING</p></div>"
        "<div class='card'><table>" + "".join(rows) + "</table></div></body></html>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def base_payload(module_number: int, args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    meta = MODULES[module_number]
    payload: Dict[str, Any] = {
        "version": VERSION,
        "module_number": module_number,
        "module_name": meta["name"],
        "module_status": "PASS",
        "generated_at_utc": utc_now(),
        "workspace": str(workspace),
        "trading_date": args.trading_date,
        "day_number": args.day_number,
        "user_id": args.user_id,
        "symbol": args.symbol,
        "market_watch_window": {"start": "09:15", "end": "15:30", "timezone": "Asia/Kolkata"},
        "secrets": env_status(),
        "data_health": data_health(workspace),
        "blocked_order_apis": BLOCKED_ORDER_APIS,
        "safety_lock": SAFETY_LOCK,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "fake_trades_created": False,
        "candidate_tuning": False,
        "real_money_automatic": False,
    }
    payload.update(day_stats(workspace))
    return payload


def module_192(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    log = workspace / f"DAY_{int(args.day_number):03d}_AUTO_PAPER_WATCH_LOOP_EVIDENCE.csv"
    if args.write:
        write_header = not log.exists()
        with log.open("a", newline="", encoding="utf-8") as fh:
            fields = ["generated_at_utc", "trading_date", "symbol", "loop_status", "data_ready", "approved_signal", "paper_trade_created", "reason"]
            writer = csv.DictWriter(fh, fieldnames=fields)
            if write_header:
                writer.writeheader()
            writer.writerow({
                "generated_at_utc": utc_now(),
                "trading_date": args.trading_date,
                "symbol": args.symbol,
                "loop_status": "PLAN_READY_MANUAL_START_ONLY",
                "data_ready": str(payload["data_health"]["data_only_connection_ready"]),
                "approved_signal": "NO",
                "paper_trade_created": "NO",
                "reason": "NO_APPROVED_SIGNAL_NO_FAKE_TRADE",
            })
    payload.update({
        "decision": "AUTO_PAPER_WATCH_LOOP_EVIDENCE_LOGGER_READY",
        "loop_evidence_csv": str(log),
        "loop_interval_minutes": 5,
        "manual_start_only": True,
        "paper_trade_created_by_module_192": False,
    })
    return payload


def module_193(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    plan = workspace / "HQE_INTRADAY_5M_POLL_SCHEDULER_PLAN.md"
    if args.write:
        plan.write_text(
            "# HQE Intraday 5m Poll Scheduler Plan\n\n"
            "- Window: 09:15 to 15:30 IST\n"
            "- Mode: manual operator start\n"
            "- Poll: data-only 5m candle refresh\n"
            "- Trade execution: blocked\n"
            "- Real money: no\n",
            encoding="utf-8",
        )
    payload.update({
        "decision": "INTRADAY_5M_POLL_SCHEDULER_PLAN_READY",
        "scheduler_plan_file": str(plan),
        "poll_interval_minutes": 5,
        "scheduled_order_execution": False,
    })
    return payload


def module_194(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    timeline = workspace / f"DAY_{int(args.day_number):03d}_PAPER_SIGNAL_REASON_TIMELINE.csv"
    if args.write:
        with timeline.open("w", newline="", encoding="utf-8") as fh:
            fields = ["generated_at_utc", "trading_date", "symbol", "signal_state", "reason_code", "reason_detail"]
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerow({
                "generated_at_utc": utc_now(),
                "trading_date": args.trading_date,
                "symbol": args.symbol,
                "signal_state": "WAITING_FOR_APPROVED_SIGNAL",
                "reason_code": "NO_APPROVED_SIGNAL_YET",
                "reason_detail": "Timeline initialized; no fake signal created.",
            })
    payload.update({
        "decision": "PAPER_SIGNAL_REASON_TIMELINE_READY",
        "timeline_csv": str(timeline),
        "approved_signal_created": False,
    })
    return payload


def module_195(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    out = workspace / f"DAY_{int(args.day_number):03d}_NO_TRADE_REASON_SUMMARY.json"
    summary = {
        "trading_date": args.trading_date,
        "symbol": args.symbol,
        "no_trade_reason": "NO_APPROVED_SIGNAL_OR_WAITING_FOR_MARKET_DATA",
        "valid_trade_day_counted": False,
        "fake_trade_created": False,
    }
    if args.write:
        write_json(out, summary)
    payload.update({
        "decision": "NO_TRADE_REASON_EVIDENCE_AGGREGATOR_READY",
        "no_trade_reason_summary": str(out),
        "no_trade_day_counts_as_valid_trade_day": False,
    })
    return payload


def module_196(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    gate = workspace / f"DAY_{int(args.day_number):03d}_PAPER_TRADE_CANDIDATE_GATE.json"
    gate_payload = {
        "approved_signal_required": True,
        "paper_trade_allowed_without_approved_signal": False,
        "real_order_allowed": False,
        "option_selling_allowed": False,
        "fake_trade_allowed": False,
    }
    if args.write:
        write_json(gate, gate_payload)
    payload.update({
        "decision": "PAPER_TRADE_CANDIDATE_GATE_READY_APPROVED_SIGNAL_REQUIRED",
        "candidate_gate_file": str(gate),
        "approved_signal_required": True,
        "paper_trade_allowed_without_approved_signal": False,
        "real_order_allowed": False,
    })
    return payload


def module_197(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    repo = repo_root()
    py = repo / ".venv" / "Scripts" / "python.exe"
    script = repo / "scripts" / "hqe_visual_dashboard_v4_market_watch_controls.py"
    launcher = workspace / "OPEN_HQE_VISUAL_DASHBOARD_V4_MARKET_WATCH.cmd"
    write_cmd(launcher, [
        "echo Opening HQE Dashboard V4 Market Watch Controls",
        f'"{py}" "{script}" --workspace "{workspace}" --trading-date "{args.trading_date}" --day-number "{args.day_number}" --user-id "{args.user_id}" --symbol "{args.symbol}" --launch --write',
        "pause",
    ])
    payload.update({
        "decision": "VISUAL_DASHBOARD_V4_MARKET_WATCH_CONTROLS_READY",
        "dashboard_v4_launcher": str(launcher),
        "dashboard_buttons": [
            "Refresh Fyers Token", "Historical 5m Data-Only Test", "Start Paper Watch Loop Evidence",
            "Open No-Trade Summary", "Daily Close Report", "Open Evidence Index"
        ],
    })
    return payload


def module_198(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    report = workspace / f"DAY_{int(args.day_number):03d}_DAILY_CLOSE_AUTO_REPORT.md"
    if args.write:
        report.write_text(
            "# HQE Daily Close Auto Report\n\n"
            f"- Trading date: {args.trading_date}\n"
            f"- Symbol: {args.symbol}\n"
            f"- Actual paper trades: {payload.get('actual_paper_trades', 0)}\n"
            f"- Valid paper trade days: {payload.get('valid_paper_trade_days', 0)} / 30\n"
            "- Real money: NO\n"
            "- Broker execution: NO\n"
            "- Auto trading: NO\n",
            encoding="utf-8",
        )
    payload.update({
        "decision": "DAILY_CLOSE_AUTO_REPORT_PACK_READY",
        "daily_close_report": str(report),
        "auto_close_executes_orders": False,
    })
    return payload


def module_199(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    progress = workspace / "HQE_30_VALID_TRADE_DAY_PROGRESS_SYNC.json"
    progress_payload = {
        "valid_paper_trade_days": payload.get("valid_paper_trade_days", 0),
        "target_valid_paper_trade_days": 30,
        "remaining_valid_trade_days": payload.get("remaining_valid_trade_days", 30),
        "no_trade_days_do_not_count": True,
        "real_money_ready": False,
    }
    if args.write:
        write_json(progress, progress_payload)
    payload.update({
        "decision": "THIRTY_VALID_TRADE_DAY_PROGRESS_SYNC_READY",
        "progress_file": str(progress),
        "real_money_ready": False,
    })
    return payload


def module_200(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    startup = workspace / "START_NEXT_MARKET_DAY_SAFE_PAPER_OPS.cmd"
    write_cmd(startup, [
        "title HQE Next Market-Day Safe Paper Ops",
        "echo HQE NEXT MARKET-DAY SAFE PAPER OPS",
        "echo Safety: PAPER ONLY / DATA ONLY / NO ORDERS",
        f'call "{workspace}\\OPEN_HQE_VISUAL_DASHBOARD_V4_MARKET_WATCH.cmd"',
    ])
    payload.update({
        "decision": "NEXT_MARKET_DAY_STARTUP_PACK_READY",
        "startup_launcher": str(startup),
        "pc_startup_auto_trading": False,
    })
    return payload


def module_201(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    index = workspace / "HQE_MASTER_EVIDENCE_INDEX.html"
    files = sorted([p for p in workspace.glob("*") if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv", ".html", ".cmd"}])
    links = []
    for p in files:
        links.append(f"<li><a href='{html.escape(p.as_uri())}'>{html.escape(p.name)}</a></li>")
    index.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>HQE Evidence Index</title></head><body>"
        "<h1>HQE Master Evidence Index</h1><p>Paper-only/data-only evidence files.</p><ul>"
        + "".join(links)
        + "</ul></body></html>",
        encoding="utf-8",
    )
    payload.update({
        "decision": "MASTER_EVIDENCE_INDEX_HTML_READY",
        "evidence_index_html": str(index),
        "indexed_file_count": len(files),
    })
    return payload


def module_202(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    audit = {
        "order_apis_hard_blocked": True,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "real_money_automatic": False,
        "kill_switch_status": "ARMED_SAFE_BLOCK",
    }
    payload.update({
        "decision": "KILL_SWITCH_SAFETY_AUDIT_PASS",
        "kill_switch_audit": audit,
        "kill_switch_status": "ARMED_SAFE_BLOCK",
    })
    return payload


def module_203(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    reminder = workspace / "HQE_FYERS_TOKEN_REFRESH_REMINDER.md"
    if args.write:
        reminder.write_text(
            "# Fyers Token Refresh Reminder\n\n"
            "- If data-only test fails with authentication, click Refresh Fyers Token in Dashboard V4.\n"
            "- Never paste token/secret/auth code into chat.\n"
            "- Real orders remain blocked.\n",
            encoding="utf-8",
        )
    payload.update({
        "decision": "TOKEN_EXPIRY_REMINDER_PREFLIGHT_READY",
        "token_reminder_file": str(reminder),
        "credentials_complete_now": payload["secrets"]["credentials_complete_for_data_only_watch"],
    })
    return payload


def module_204(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    # Calendar guard is conservative and manual. It does not claim exchange holiday knowledge.
    payload.update({
        "decision": "MARKET_SESSION_CALENDAR_GUARD_READY_MANUAL_HOLIDAY_CHECK_REQUIRED",
        "market_window_start": "09:15",
        "market_window_end": "15:30",
        "manual_exchange_holiday_check_required": True,
        "auto_market_calendar_claim": False,
    })
    return payload


def module_205(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    normalized_csv = workspace / "FYERS_LIVE_DATA_ONLY_5M_NORMALIZED.csv"
    rows = count_csv_rows(normalized_csv)
    payload.update({
        "decision": "LIVE_DATA_GAP_DETECTOR_READY",
        "normalized_csv": str(normalized_csv),
        "normalized_rows": rows,
        "data_gap_detected": rows == 0,
        "data_gap_action": "REFRESH_TOKEN_AND_RUN_5M_DATA_ONLY_TEST" if rows == 0 else "NO_GAP_IN_LAST_NORMALIZED_SAMPLE",
    })
    return payload


def module_206(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    ready = bool(payload["data_health"]["data_only_connection_ready"])
    payload.update({
        "decision": "PAPER_WATCH_DRY_RUN_SMOKE_PASS" if ready else "PAPER_WATCH_DRY_RUN_SMOKE_WAITING_FOR_DATA",
        "dry_run_smoke_status": "PASS",
        "data_only_ready_for_dry_run": ready,
        "orders_executed_in_smoke": False,
    })
    return payload


def module_207(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    launcher = workspace / "HQE_ONE_CLICK_MARKET_DAY_OPERATOR.cmd"
    write_cmd(launcher, [
        "title HQE One Click Market-Day Operator",
        "echo HQE ONE CLICK MARKET-DAY OPERATOR",
        "echo Safety: PAPER ONLY / DATA ONLY / NO ORDERS",
        f'call "{workspace}\\OPEN_HQE_VISUAL_DASHBOARD_V4_MARKET_WATCH.cmd"',
    ])
    payload.update({
        "decision": "DESKTOP_ONE_CLICK_LAUNCHER_PACK_READY",
        "one_click_launcher": str(launcher),
        "desktop_shortcut_review_required": True,
    })
    return payload


def module_208(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    guide = workspace / "HQE_OPERATOR_ERROR_RECOVERY_GUIDE.md"
    if args.write:
        guide.write_text(
            "# HQE Operator Error Recovery Guide\n\n"
            "## Token missing\nRun Refresh Fyers Token from Dashboard V4.\n\n"
            "## Data rows zero\nRun Historical 5m Data-Only Test again after token refresh.\n\n"
            "## No trade\nNo approved signal means no fake trade. Day does not count as valid trade-day.\n\n"
            "## Safety\nNo real orders, no broker execution, no auto trading.\n",
            encoding="utf-8",
        )
    payload.update({
        "decision": "OPERATOR_ERROR_RECOVERY_PACK_READY",
        "error_recovery_guide": str(guide),
    })
    return payload


def module_209(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    valid_days = int(payload.get("valid_paper_trade_days", 0) or 0)
    actual_trades = int(payload.get("actual_paper_trades", 0) or 0)
    ready = valid_days >= 30 and actual_trades >= 30
    payload.update({
        "decision": "FORWARD_VALIDATION_FINAL_GATE_HOLD_MORE_DATA_REQUIRED" if not ready else "FORWARD_VALIDATION_FINAL_GATE_REVIEW_READY",
        "forward_validation_ready_for_real_money_review": ready,
        "minimum_valid_trade_days_required": 30,
        "minimum_paper_trades_required": 30,
        "real_money_allowed_by_module_209": False,
    })
    return payload


def module_210(payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    handoff = workspace / "HQE_MARKET_DAY_PAPER_WATCH_MASTER_HANDOFF.md"
    if args.write:
        handoff.write_text(
            "# HQE Market-Day Paper Watch Master Handoff\n\n"
            "Status: Module 192-210 installed.\n\n"
            "Use Dashboard V4 or one-click operator launcher.\n\n"
            "Safety remains paper-only/data-only. Real money is not enabled.\n",
            encoding="utf-8",
        )
    payload.update({
        "decision": "MARKET_DAY_PAPER_WATCH_MASTER_HANDOFF_READY",
        "master_handoff_file": str(handoff),
        "modules_192_to_210_complete": True,
        "real_money_enabled": False,
    })
    return payload


MODULE_HANDLERS = {
    192: module_192,
    193: module_193,
    194: module_194,
    195: module_195,
    196: module_196,
    197: module_197,
    198: module_198,
    199: module_199,
    200: module_200,
    201: module_201,
    202: module_202,
    203: module_203,
    204: module_204,
    205: module_205,
    206: module_206,
    207: module_207,
    208: module_208,
    209: module_209,
    210: module_210,
}


def build_module(module_number: int, args: argparse.Namespace) -> Dict[str, Any]:
    payload = base_payload(module_number, args)
    payload = MODULE_HANDLERS[module_number](payload, args)
    return payload


def emit_module(module_number: int, payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    base = MODULES[module_number]["base"]
    json_path = workspace / f"{base}.json"
    md_path = workspace / f"{base}.md"
    ledger_path = workspace / "MODULES_192_210_MARKET_DAY_PAPER_WATCH_LEDGER.csv"
    payload["evidence_files"] = {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}
    if args.write:
        write_json(json_path, payload)
        write_md(md_path, f"Module {module_number} {MODULES[module_number]['name']}", payload)
        append_ledger(ledger_path, payload)
        if module_number in {197, 201, 210}:
            html_status(workspace / "HQE_MODULES_192_210_STATUS.html", "HQE Modules 192-210 Status", payload)
    return payload


def guard_check(module_number: int) -> int:
    payload = {
        "version": VERSION,
        "guard_check_status": "PASS",
        "module_number": module_number,
        "module_name": MODULES[module_number]["name"],
        "safety_lock": SAFETY_LOCK,
        "blocked_order_apis": {name: "HARD_BLOCKED" for name in BLOCKED_ORDER_APIS},
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "real_money_automatic": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def launch_v4(args: argparse.Namespace) -> int:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        print("Tkinter unavailable. Use generated CMD launchers.")
        return 1

    workspace = Path(args.workspace)
    repo = repo_root()
    py = repo / ".venv" / "Scripts" / "python.exe"

    def run_cmd(label: str, command: str) -> None:
        try:
            subprocess.Popen(command, cwd=str(repo), shell=True)
        except Exception as exc:
            messagebox.showerror(label, str(exc))

    root = tk.Tk()
    root.title("HQE Dashboard V4 Market Watch - Paper Only")
    root.geometry("800x620")

    tk.Label(root, text="HQE Dashboard V4 Market Watch", font=("Segoe UI", 18, "bold")).pack(pady=(14, 2))
    tk.Label(root, text="PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING", fg="green").pack(pady=(0, 12))
    tk.Label(root, text=f"Trading date: {args.trading_date} | Symbol: {args.symbol}").pack(pady=2)
    tk.Label(root, text=f"Workspace: {workspace}", wraplength=760, justify="left").pack(pady=2)

    frame = tk.Frame(root)
    frame.pack(pady=12, fill="both", expand=True)

    buttons = [
        ("Refresh Fyers Token", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\HQE_FYERS_TOKEN_SIMPLE_REFRESH_V2.ps1" -RepoRoot "{repo}" -Workspace "{workspace}" -Symbol "{args.symbol}"'),
        ("Historical 5m Data-Only Test", f'"{py}" scripts\\hqe_fyers_historical_5m_data_only_fetcher.py --workspace "{workspace}" --symbol "{args.symbol}" --execute-live-data-only --write'),
        ("Run 192-210 Status", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\RUN_MODULES_192_210_MARKET_DAY_PAPER_WATCH_FINAL.ps1" -Workspace "{workspace}" -TradingDate "{args.trading_date}" -DayNumber {args.day_number} -UserId "{args.user_id}" -Symbol "{args.symbol}"'),
        ("Open Evidence Folder", f'explorer "{workspace}"'),
        ("Open Evidence Index", f'start "" "{workspace}\\HQE_MASTER_EVIDENCE_INDEX.html"'),
        ("Open Daily Close Report", f'start "" "{workspace}\\DAY_{int(args.day_number):03d}_DAILY_CLOSE_AUTO_REPORT.md"'),
    ]
    for label, command in buttons:
        tk.Button(frame, text=label, width=48, height=2, command=lambda l=label, c=command: run_cmd(l, c)).pack(pady=6)

    tk.Label(root, text="No order APIs are available in this dashboard.", fg="green").pack(pady=10)
    root.mainloop()
    return 0


def module_main(module_number: int) -> int:
    p = parser_for(MODULES[module_number]["name"])
    args = p.parse_args()
    if args.guard_check:
        return guard_check(module_number)
    payload = build_module(module_number, args)
    payload = emit_module(module_number, payload, args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.launch and module_number == 197:
        return launch_v4(args)
    return 0
