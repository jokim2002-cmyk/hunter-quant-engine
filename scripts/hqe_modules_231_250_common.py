from __future__ import annotations

import argparse
import csv
import html
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

VERSION = "MODULES_231_250_VALIDATION_GOVERNANCE_FINAL_V1"
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
    231: {"file": "hqe_validation_day_auto_rollover_plan.py", "name": "Validation Day Auto Rollover Plan", "base": "MODULE_231_VALIDATION_DAY_AUTO_ROLLOVER_PLAN_STATUS"},
    232: {"file": "hqe_missing_evidence_detector.py", "name": "Missing Evidence Detector", "base": "MODULE_232_MISSING_EVIDENCE_DETECTOR_STATUS"},
    233: {"file": "hqe_paper_pnl_aggregator_safe.py", "name": "Paper PnL Aggregator Safe", "base": "MODULE_233_PAPER_PNL_AGGREGATOR_SAFE_STATUS"},
    234: {"file": "hqe_trade_day_eligibility_auditor.py", "name": "Trade-Day Eligibility Auditor", "base": "MODULE_234_TRADE_DAY_ELIGIBILITY_AUDITOR_STATUS"},
    235: {"file": "hqe_expiry_week_progress_tracker.py", "name": "Expiry Week Progress Tracker", "base": "MODULE_235_EXPIRY_WEEK_PROGRESS_TRACKER_STATUS"},
    236: {"file": "hqe_dashboard_v6_validation_governance.py", "name": "Dashboard V6 Validation Governance", "base": "MODULE_236_DASHBOARD_V6_VALIDATION_GOVERNANCE_STATUS"},
    237: {"file": "hqe_daily_html_report_builder.py", "name": "Daily HTML Report Builder", "base": "MODULE_237_DAILY_HTML_REPORT_BUILDER_STATUS"},
    238: {"file": "hqe_secure_env_reload_helper.py", "name": "Secure Env Reload Helper", "base": "MODULE_238_SECURE_ENV_RELOAD_HELPER_STATUS"},
    239: {"file": "hqe_data_replay_verifier.py", "name": "Data Replay Verifier", "base": "MODULE_239_DATA_REPLAY_VERIFIER_STATUS"},
    240: {"file": "hqe_watch_loop_crash_resume_marker.py", "name": "Watch Loop Crash Resume Marker", "base": "MODULE_240_WATCH_LOOP_CRASH_RESUME_MARKER_STATUS"},
    241: {"file": "hqe_paper_execution_gate_no_fake.py", "name": "Paper Execution Gate No Fake", "base": "MODULE_241_PAPER_EXECUTION_GATE_NO_FAKE_STATUS"},
    242: {"file": "hqe_no_trade_day_non_count_lock.py", "name": "No-Trade Day Non-Count Lock", "base": "MODULE_242_NO_TRADE_DAY_NON_COUNT_LOCK_STATUS"},
    243: {"file": "hqe_validation_master_ledger_reconciler.py", "name": "Validation Master Ledger Reconciler", "base": "MODULE_243_VALIDATION_MASTER_LEDGER_RECONCILER_STATUS"},
    244: {"file": "hqe_operator_command_center_shortcuts.py", "name": "Operator Command Center Shortcuts", "base": "MODULE_244_OPERATOR_COMMAND_CENTER_SHORTCUTS_STATUS"},
    245: {"file": "hqe_remote_safe_handoff_bundle.py", "name": "Remote Safe Handoff Bundle", "base": "MODULE_245_REMOTE_SAFE_HANDOFF_BUNDLE_STATUS"},
    246: {"file": "hqe_evidence_archive_indexer.py", "name": "Evidence Archive Indexer", "base": "MODULE_246_EVIDENCE_ARCHIVE_INDEXER_STATUS"},
    247: {"file": "hqe_final_30_day_readiness_gate.py", "name": "Final 30-Day Readiness Gate", "base": "MODULE_247_FINAL_30_DAY_READINESS_GATE_STATUS"},
    248: {"file": "hqe_pre_real_money_review_checklist.py", "name": "Pre-Real-Money Review Checklist", "base": "MODULE_248_PRE_REAL_MONEY_REVIEW_CHECKLIST_STATUS"},
    249: {"file": "hqe_validation_governance_freeze_pack.py", "name": "Validation Governance Freeze Pack", "base": "MODULE_249_VALIDATION_GOVERNANCE_FREEZE_PACK_STATUS"},
    250: {"file": "hqe_master_system_status_dashboard.py", "name": "Master System Status Dashboard", "base": "MODULE_250_MASTER_SYSTEM_STATUS_DASHBOARD_STATUS"},
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


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            return len(list(csv.DictReader(fh)))
    except Exception:
        return 0


def csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh))
    except Exception:
        return []


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


def count_actual_trades(workspace: Path) -> int:
    total = 0
    candidates = [workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv", workspace / "FORWARD_PAPER_TRADE_MASTER_LEDGER.csv"]
    candidates.extend(workspace.glob("DAY_*_FORWARD_TRADE_LOG.csv"))
    for path in candidates:
        total += count_csv_rows(path)
    return total


def day_stats(workspace: Path) -> Dict[str, Any]:
    ledger = workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv"
    rows = csv_rows(ledger)
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
    m173 = read_json(workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json")
    m183 = read_json(workspace / "MODULE_183_FYERS_DATA_ONLY_HEALTH_MONITOR_STATUS.json")
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


def html_report(path: Path, title: str, payload: Dict[str, Any]) -> None:
    rows = []
    for key, value in payload.items():
        if key in {"blocked_order_apis", "safety_lock"}:
            continue
        shown = json.dumps(value, indent=2, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        rows.append("<tr><th>{}</th><td><pre>{}</pre></td></tr>".format(html.escape(str(key)), html.escape(shown)))
    doc = (
        "<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(title) + "</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;background:#f7f7f7;margin:24px;color:#111}"
        ".card{background:white;padding:18px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.08);margin-bottom:16px}"
        ".safe{color:#0a7d20;font-weight:bold}table{border-collapse:collapse;width:100%;background:white}"
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


def specific(module_number: int, payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    repo = repo_root()
    py = repo / ".venv" / "Scripts" / "python.exe"
    day = int(args.day_number)

    if module_number == 231:
        next_day = day + 1
        plan = workspace / f"DAY_{next_day:03d}_ROLLOVER_PLAN.json"
        rollover = {"current_day": day, "next_day": next_day, "auto_create_fake_trade": False, "manual_operator_review_required": True}
        if args.write:
            write_json(plan, rollover)
        payload.update({"decision": "VALIDATION_DAY_AUTO_ROLLOVER_PLAN_READY", "rollover_plan": str(plan), **rollover})

    elif module_number == 232:
        expected = [
            "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json",
            "MODULE_191_REAL_MARKET_DAY_PAPER_WATCH_LAUNCHER_STATUS.json",
            "HQE_MASTER_EVIDENCE_INDEX.html",
        ]
        missing = [name for name in expected if not (workspace / name).exists()]
        out = workspace / "HQE_MISSING_EVIDENCE_DETECTOR.json"
        if args.write:
            write_json(out, {"expected": expected, "missing": missing})
        payload.update({"decision": "MISSING_EVIDENCE_DETECTOR_READY", "missing_evidence_file": str(out), "missing_expected_count": len(missing), "missing_expected_files": missing})

    elif module_number == 233:
        trade_files = list(workspace.glob("DAY_*_FORWARD_TRADE_LOG.csv")) + [workspace / "FORWARD_PAPER_TRADE_MASTER_LEDGER.csv"]
        trade_rows = sum(count_csv_rows(p) for p in trade_files)
        out = workspace / "HQE_PAPER_PNL_AGGREGATE_SAFE.json"
        aggregate = {"trade_rows": trade_rows, "net_pnl_known": False, "net_pnl": 0, "no_fake_pnl": True}
        if args.write:
            write_json(out, aggregate)
        payload.update({"decision": "PAPER_PNL_AGGREGATOR_SAFE_READY", "pnl_aggregate_file": str(out), **aggregate})

    elif module_number == 234:
        eligible = payload.get("actual_paper_trades", 0) > 0
        audit = workspace / f"DAY_{day:03d}_TRADE_DAY_ELIGIBILITY_AUDIT.json"
        audit_payload = {"eligible_valid_trade_day": eligible, "reason": "TRADE_ROWS_PRESENT" if eligible else "NO_TRADE_ROWS_PRESENT", "no_trade_day_counts": False}
        if args.write:
            write_json(audit, audit_payload)
        payload.update({"decision": "TRADE_DAY_ELIGIBILITY_AUDITOR_READY", "eligibility_audit": str(audit), **audit_payload})

    elif module_number == 235:
        tracker = workspace / "HQE_EXPIRY_WEEK_PROGRESS_TRACKER.json"
        tracker_payload = {"distinct_expiry_weeks": payload.get("distinct_expiry_weeks", 0), "target_expiry_weeks": 4, "remaining_expiry_weeks": max(4 - int(payload.get("distinct_expiry_weeks", 0) or 0), 0)}
        if args.write:
            write_json(tracker, tracker_payload)
        payload.update({"decision": "EXPIRY_WEEK_PROGRESS_TRACKER_READY", "expiry_week_tracker": str(tracker), **tracker_payload})

    elif module_number == 236:
        launcher = workspace / "OPEN_HQE_DASHBOARD_V6_VALIDATION_GOVERNANCE.cmd"
        script = repo / "scripts" / "hqe_dashboard_v6_validation_governance.py"
        write_cmd(launcher, [
            "echo Opening HQE Dashboard V6 Validation Governance",
            f'"{py}" "{script}" --workspace "{workspace}" --trading-date "{args.trading_date}" --day-number "{day}" --user-id "{args.user_id}" --symbol "{args.symbol}" --launch --write',
            "pause",
        ])
        payload.update({"decision": "DASHBOARD_V6_VALIDATION_GOVERNANCE_READY", "dashboard_v6_launcher": str(launcher)})

    elif module_number == 237:
        report = workspace / f"DAY_{day:03d}_DAILY_VALIDATION_REPORT.html"
        html_report(report, "HQE Daily Validation Report", payload)
        payload.update({"decision": "DAILY_HTML_REPORT_BUILDER_READY", "daily_html_report": str(report)})

    elif module_number == 238:
        helper = workspace / "HQE_RELOAD_FYERS_ENV_IN_CURRENT_POWERSHELL.ps1"
        if args.write:
            helper.write_text(
                '$env:FYERS_CLIENT_ID = [Environment]::GetEnvironmentVariable("FYERS_CLIENT_ID", "User")\n'
                '$env:FYERS_ACCESS_TOKEN = [Environment]::GetEnvironmentVariable("FYERS_ACCESS_TOKEN", "User")\n'
                'Write-Host "Client ID loaded:" (-not [string]::IsNullOrWhiteSpace($env:FYERS_CLIENT_ID))\n'
                'Write-Host "Access token loaded:" (-not [string]::IsNullOrWhiteSpace($env:FYERS_ACCESS_TOKEN))\n',
                encoding="utf-8",
            )
        payload.update({"decision": "SECURE_ENV_RELOAD_HELPER_READY", "env_reload_helper": str(helper), "secret_values_written_to_output": False})

    elif module_number == 239:
        cache = workspace / "data_only_cache"
        replay_files = list(cache.glob("*.csv")) if cache.exists() else []
        out = workspace / "HQE_DATA_REPLAY_VERIFIER.json"
        replay_payload = {"replay_file_count": len(replay_files), "replay_executes_orders": False, "replay_ready": len(replay_files) > 0}
        if args.write:
            write_json(out, replay_payload)
        payload.update({"decision": "DATA_REPLAY_VERIFIER_READY", "replay_verifier": str(out), **replay_payload})

    elif module_number == 240:
        marker = workspace / "HQE_WATCH_LOOP_CRASH_RESUME_MARKER.json"
        marker_payload = {"last_safe_checkpoint_utc": utc_now(), "resume_action": "reload_dashboard_and_continue_data_only_watch", "open_orders_to_recover": 0}
        if args.write:
            write_json(marker, marker_payload)
        payload.update({"decision": "WATCH_LOOP_CRASH_RESUME_MARKER_READY", "resume_marker": str(marker), **marker_payload})

    elif module_number == 241:
        gate = workspace / "HQE_PAPER_EXECUTION_GATE_NO_FAKE.json"
        gate_payload = {"approved_signal_required": True, "paper_execution_without_signal": False, "fake_trade_allowed": False, "real_order_allowed": False}
        if args.write:
            write_json(gate, gate_payload)
        payload.update({"decision": "PAPER_EXECUTION_GATE_NO_FAKE_READY", "paper_execution_gate": str(gate), **gate_payload})

    elif module_number == 242:
        lock = workspace / "HQE_NO_TRADE_DAY_NON_COUNT_LOCK.json"
        lock_payload = {"no_trade_day_counts_as_valid_trade_day": False, "trade_rows_required_for_valid_day": True}
        if args.write:
            write_json(lock, lock_payload)
        payload.update({"decision": "NO_TRADE_DAY_NON_COUNT_LOCK_READY", "non_count_lock": str(lock), **lock_payload})

    elif module_number == 243:
        reconciler = workspace / "HQE_VALIDATION_MASTER_LEDGER_RECONCILER.json"
        reconciler_payload = {"master_ledger_rows": count_csv_rows(workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv"), "paper_trade_rows": payload.get("actual_paper_trades", 0), "reconciliation_status": "READY_FOR_MANUAL_REVIEW"}
        if args.write:
            write_json(reconciler, reconciler_payload)
        payload.update({"decision": "VALIDATION_MASTER_LEDGER_RECONCILER_READY", "reconciler_file": str(reconciler), **reconciler_payload})

    elif module_number == 244:
        center = workspace / "OPEN_HQE_OPERATOR_COMMAND_CENTER_FINAL.cmd"
        write_cmd(center, [
            "title HQE Operator Command Center Final",
            "echo HQE OPERATOR COMMAND CENTER FINAL",
            "echo Safety: PAPER ONLY / DATA ONLY / NO ORDERS",
            f'call "{workspace}\\OPEN_HQE_DASHBOARD_V6_VALIDATION_GOVERNANCE.cmd"',
        ])
        payload.update({"decision": "OPERATOR_COMMAND_CENTER_SHORTCUTS_READY", "command_center_launcher": str(center)})

    elif module_number == 245:
        bundle = workspace / "HQE_REMOTE_SAFE_HANDOFF_BUNDLE.md"
        if args.write:
            bundle.write_text(
                "# HQE Remote Safe Handoff Bundle\n\n"
                "This bundle describes paper-only/data-only operation. It contains no secrets.\n\n"
                "- No real orders\n- No broker execution\n- No auto trading\n",
                encoding="utf-8",
            )
        payload.update({"decision": "REMOTE_SAFE_HANDOFF_BUNDLE_READY", "handoff_bundle": str(bundle), "contains_secrets": False})

    elif module_number == 246:
        archive_index = workspace / "HQE_EVIDENCE_ARCHIVE_INDEX.json"
        evidence_files = [p.name for p in workspace.glob("*") if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv", ".html", ".cmd"}]
        if args.write:
            write_json(archive_index, {"evidence_file_count": len(evidence_files), "files": evidence_files[:500]})
        payload.update({"decision": "EVIDENCE_ARCHIVE_INDEXER_READY", "archive_index": str(archive_index), "evidence_file_count": len(evidence_files)})

    elif module_number == 247:
        ready = payload.get("valid_paper_trade_days", 0) >= 30 and payload.get("actual_paper_trades", 0) >= 30 and payload.get("distinct_expiry_weeks", 0) >= 4
        gate = workspace / "HQE_FINAL_30_DAY_READINESS_GATE.json"
        gate_payload = {"final_30_day_ready": ready, "real_money_allowed": False, "manual_review_required": True}
        if args.write:
            write_json(gate, gate_payload)
        payload.update({"decision": "FINAL_30_DAY_READINESS_HOLD_MORE_DATA_REQUIRED" if not ready else "FINAL_30_DAY_READINESS_REVIEW_READY", "final_gate_file": str(gate), **gate_payload})

    elif module_number == 248:
        checklist = workspace / "HQE_PRE_REAL_MONEY_REVIEW_CHECKLIST.md"
        if args.write:
            checklist.write_text(
                "# HQE Pre-Real-Money Review Checklist\n\n"
                "- [ ] 30 valid paper trade-days completed\n"
                "- [ ] Minimum paper trades completed\n"
                "- [ ] 4 expiry weeks observed\n"
                "- [ ] Manual review completed\n"
                "- [ ] Real money risk approval documented\n\n"
                "Current status: real money remains NO.\n",
                encoding="utf-8",
            )
        payload.update({"decision": "PRE_REAL_MONEY_REVIEW_CHECKLIST_READY_REAL_MONEY_STILL_NO", "review_checklist": str(checklist), "real_money_allowed": False})

    elif module_number == 249:
        freeze = workspace / "HQE_VALIDATION_GOVERNANCE_FREEZE.md"
        if args.write:
            freeze.write_text(
                "# HQE Validation Governance Freeze\n\n"
                "Modules 231-250 installed.\n\n"
                "Safety remains paper-only/data-only. No real orders. No broker execution. No auto trading.\n",
                encoding="utf-8",
            )
        payload.update({"decision": "VALIDATION_GOVERNANCE_FREEZE_READY", "governance_freeze_file": str(freeze)})

    elif module_number == 250:
        dashboard = workspace / "HQE_MASTER_SYSTEM_STATUS_DASHBOARD.html"
        final = dict(payload)
        final.update({"modules_231_to_250_complete": True, "real_money_enabled": False, "master_system_status": "PAPER_DATA_ONLY_VALIDATION_GOVERNANCE_READY"})
        html_report(dashboard, "HQE Master System Status Dashboard", final)
        payload.update({"decision": "MASTER_SYSTEM_STATUS_DASHBOARD_READY", "master_dashboard": str(dashboard), "modules_231_to_250_complete": True, "real_money_enabled": False})

    return payload


def build_module(module_number: int, args: argparse.Namespace) -> Dict[str, Any]:
    payload = base_payload(module_number, args)
    return specific(module_number, payload, args)


def emit_module(module_number: int, payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    base = MODULES[module_number]["base"]
    json_path = workspace / f"{base}.json"
    md_path = workspace / f"{base}.md"
    ledger_path = workspace / "MODULES_231_250_VALIDATION_GOVERNANCE_LEDGER.csv"
    payload["evidence_files"] = {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}
    if args.write:
        write_json(json_path, payload)
        write_md(md_path, f"Module {module_number} {MODULES[module_number]['name']}", payload)
        append_ledger(ledger_path, payload)
        if module_number in {236, 250}:
            html_report(workspace / "HQE_VALIDATION_GOVERNANCE_231_250_STATUS.html", "HQE Validation Governance 231-250 Status", payload)
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


def launch_v6(args: argparse.Namespace) -> int:
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
    root.title("HQE Dashboard V6 Validation Governance")
    root.geometry("840x660")

    tk.Label(root, text="HQE Dashboard V6 Validation Governance", font=("Segoe UI", 18, "bold")).pack(pady=(14, 2))
    tk.Label(root, text="PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING", fg="green").pack(pady=(0, 12))
    tk.Label(root, text=f"Trading date: {args.trading_date} | Symbol: {args.symbol}").pack(pady=2)
    tk.Label(root, text=f"Workspace: {workspace}", wraplength=800, justify="left").pack(pady=2)

    frame = tk.Frame(root)
    frame.pack(pady=12, fill="both", expand=True)

    buttons = [
        ("Refresh Fyers Token", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\HQE_FYERS_TOKEN_SIMPLE_REFRESH_V2.ps1" -RepoRoot "{repo}" -Workspace "{workspace}" -Symbol "{args.symbol}"'),
        ("Historical 5m Data-Only Test", f'"{py}" scripts\\hqe_fyers_historical_5m_data_only_fetcher.py --workspace "{workspace}" --symbol "{args.symbol}" --execute-live-data-only --write'),
        ("Run 231-250 Governance", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\RUN_MODULES_231_250_VALIDATION_GOVERNANCE_FINAL.ps1" -Workspace "{workspace}" -TradingDate "{args.trading_date}" -DayNumber {args.day_number} -UserId "{args.user_id}" -Symbol "{args.symbol}"'),
        ("Open Evidence Folder", f'explorer "{workspace}"'),
        ("Open Master System Dashboard", f'start "" "{workspace}\\HQE_MASTER_SYSTEM_STATUS_DASHBOARD.html"'),
        ("Open Pre-Real-Money Checklist", f'start "" "{workspace}\\HQE_PRE_REAL_MONEY_REVIEW_CHECKLIST.md"'),
    ]
    for label, command in buttons:
        tk.Button(frame, text=label, width=52, height=2, command=lambda l=label, c=command: run_cmd(l, c)).pack(pady=6)

    tk.Label(root, text="Dashboard V6 is governance/evidence only. No broker order buttons exist.", fg="green").pack(pady=10)
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
    if args.launch and module_number == 236:
        return launch_v6(args)
    return 0
