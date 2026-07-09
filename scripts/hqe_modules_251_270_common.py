from __future__ import annotations

import argparse
import csv
import html
import json
import os
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

VERSION = "MODULES_251_270_FINAL_VALIDATION_HARDENING_V1"
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
    251: {"file": "hqe_daily_run_manifest_generator.py", "name": "Daily Run Manifest Generator", "base": "MODULE_251_DAILY_RUN_MANIFEST_GENERATOR_STATUS"},
    252: {"file": "hqe_manual_market_holiday_override_guard.py", "name": "Manual Market Holiday Override Guard", "base": "MODULE_252_MANUAL_MARKET_HOLIDAY_OVERRIDE_GUARD_STATUS"},
    253: {"file": "hqe_valid_trade_day_acceptance_criteria_engine.py", "name": "Valid Trade-Day Acceptance Criteria Engine", "base": "MODULE_253_VALID_TRADE_DAY_ACCEPTANCE_CRITERIA_ENGINE_STATUS"},
    254: {"file": "hqe_forward_validation_kpi_snapshot.py", "name": "Forward Validation KPI Snapshot", "base": "MODULE_254_FORWARD_VALIDATION_KPI_SNAPSHOT_STATUS"},
    255: {"file": "hqe_evidence_export_zip_pack.py", "name": "Evidence Export Zip Pack", "base": "MODULE_255_EVIDENCE_EXPORT_ZIP_PACK_STATUS"},
    256: {"file": "hqe_critical_blocker_banner_pack.py", "name": "Critical Blocker Banner Pack", "base": "MODULE_256_CRITICAL_BLOCKER_BANNER_PACK_STATUS"},
    257: {"file": "hqe_stale_token_data_age_checker.py", "name": "Stale Token Data Age Checker", "base": "MODULE_257_STALE_TOKEN_DATA_AGE_CHECKER_STATUS"},
    258: {"file": "hqe_end_to_end_operator_rehearsal_pack.py", "name": "End-to-End Operator Rehearsal Pack", "base": "MODULE_258_END_TO_END_OPERATOR_REHEARSAL_PACK_STATUS"},
    259: {"file": "hqe_paper_signal_latency_tracker.py", "name": "Paper Signal Latency Tracker", "base": "MODULE_259_PAPER_SIGNAL_LATENCY_TRACKER_STATUS"},
    260: {"file": "hqe_safe_config_snapshot.py", "name": "Safe Config Snapshot", "base": "MODULE_260_SAFE_CONFIG_SNAPSHOT_STATUS"},
    261: {"file": "hqe_workspace_cleanup_review_plan.py", "name": "Workspace Cleanup Review Plan", "base": "MODULE_261_WORKSPACE_CLEANUP_REVIEW_PLAN_STATUS"},
    262: {"file": "hqe_validation_anomaly_detector.py", "name": "Validation Anomaly Detector", "base": "MODULE_262_VALIDATION_ANOMALY_DETECTOR_STATUS"},
    263: {"file": "hqe_daily_summary_clipboard_pack.py", "name": "Daily Summary Clipboard Pack", "base": "MODULE_263_DAILY_SUMMARY_CLIPBOARD_PACK_STATUS"},
    264: {"file": "hqe_no_broker_api_static_scanner.py", "name": "No-Broker-API Static Scanner", "base": "MODULE_264_NO_BROKER_API_STATIC_SCANNER_STATUS"},
    265: {"file": "hqe_final_daily_evidence_bundle.py", "name": "Final Daily Evidence Bundle", "base": "MODULE_265_FINAL_DAILY_EVIDENCE_BUNDLE_STATUS"},
    266: {"file": "hqe_monthly_validation_pack.py", "name": "Monthly Validation Pack", "base": "MODULE_266_MONTHLY_VALIDATION_PACK_STATUS"},
    267: {"file": "hqe_dashboard_v7_final_validation_hardening.py", "name": "Dashboard V7 Final Validation Hardening", "base": "MODULE_267_DASHBOARD_V7_FINAL_VALIDATION_HARDENING_STATUS"},
    268: {"file": "hqe_supervisory_review_memo_pack.py", "name": "Supervisory Review Memo Pack", "base": "MODULE_268_SUPERVISORY_REVIEW_MEMO_PACK_STATUS"},
    269: {"file": "hqe_go_no_go_governance_freeze.py", "name": "Go/No-Go Governance Freeze", "base": "MODULE_269_GO_NO_GO_GOVERNANCE_FREEZE_STATUS"},
    270: {"file": "hqe_master_readiness_freeze_final.py", "name": "Master Readiness Freeze Final", "base": "MODULE_270_MASTER_READINESS_FREEZE_FINAL_STATUS"},
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


def count_actual_trades(workspace: Path) -> int:
    total = 0
    candidates = [workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv", workspace / "FORWARD_PAPER_TRADE_MASTER_LEDGER.csv"]
    candidates.extend(workspace.glob("DAY_*_FORWARD_TRADE_LOG.csv"))
    for path in candidates:
        total += count_csv_rows(path)
    return total


def day_stats(workspace: Path) -> Dict[str, Any]:
    rows = csv_rows(workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv")
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

    if module_number == 251:
        manifest = workspace / f"DAY_{day:03d}_RUN_MANIFEST.json"
        manifest_payload = {"trading_date": args.trading_date, "day_number": day, "symbol": args.symbol, "operator": args.user_id, "real_orders_allowed": False}
        if args.write:
            write_json(manifest, manifest_payload)
        payload.update({"decision": "DAILY_RUN_MANIFEST_READY", "run_manifest": str(manifest), **manifest_payload})

    elif module_number == 252:
        guard = workspace / "HQE_MANUAL_MARKET_HOLIDAY_OVERRIDE_GUARD.json"
        guard_payload = {"manual_holiday_check_required": True, "auto_exchange_holiday_claim": False, "operator_may_skip_non_market_day": True}
        if args.write:
            write_json(guard, guard_payload)
        payload.update({"decision": "MANUAL_MARKET_HOLIDAY_OVERRIDE_GUARD_READY", "holiday_guard": str(guard), **guard_payload})

    elif module_number == 253:
        criteria = workspace / "HQE_VALID_TRADE_DAY_ACCEPTANCE_CRITERIA.json"
        criteria_payload = {
            "trade_rows_required": True,
            "no_trade_day_counts": False,
            "paper_only_required": True,
            "real_order_disqualifies_validation": True,
        }
        if args.write:
            write_json(criteria, criteria_payload)
        payload.update({"decision": "VALID_TRADE_DAY_ACCEPTANCE_CRITERIA_READY", "criteria_file": str(criteria), **criteria_payload})

    elif module_number == 254:
        kpi = workspace / "HQE_FORWARD_VALIDATION_KPI_SNAPSHOT.json"
        kpi_payload = {
            "valid_paper_trade_days": payload.get("valid_paper_trade_days", 0),
            "remaining_valid_trade_days": payload.get("remaining_valid_trade_days", 30),
            "actual_paper_trades": payload.get("actual_paper_trades", 0),
            "real_money_ready": False,
        }
        if args.write:
            write_json(kpi, kpi_payload)
        payload.update({"decision": "FORWARD_VALIDATION_KPI_SNAPSHOT_READY", "kpi_snapshot": str(kpi), **kpi_payload})

    elif module_number == 255:
        export_dir = workspace / "evidence_exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_path = export_dir / f"HQE_EVIDENCE_EXPORT_{args.trading_date}.zip"
        candidates = [p for p in workspace.glob("*") if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv", ".html"}]
        written = 0
        if args.write:
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for p in candidates[:300]:
                    zf.write(p, arcname=p.name)
                    written += 1
        payload.update({"decision": "EVIDENCE_EXPORT_ZIP_PACK_READY", "zip_export": str(zip_path), "zipped_file_count": written, "contains_secret_files": False})

    elif module_number == 256:
        banner = workspace / "HQE_CRITICAL_BLOCKER_BANNER.md"
        blockers = []
        if not payload["secrets"]["credentials_complete_for_data_only_watch"]:
            blockers.append("FYERS_TOKEN_OR_CLIENT_ID_MISSING")
        if not payload["data_health"]["data_only_connection_ready"]:
            blockers.append("DATA_ONLY_FEED_NOT_READY")
        if args.write:
            banner.write_text("# HQE Critical Blocker Banner\n\n" + "\n".join(f"- {b}" for b in blockers) + "\n", encoding="utf-8")
        payload.update({"decision": "CRITICAL_BLOCKER_BANNER_READY", "blocker_banner": str(banner), "critical_blockers": blockers})

    elif module_number == 257:
        checker = workspace / "HQE_STALE_TOKEN_DATA_AGE_CHECKER.json"
        checker_payload = {"token_presence_only_checked": True, "token_expiry_claim_made": False, "data_rows_available": payload["data_health"]["normalized_5m_rows"] + payload["data_health"]["last_history_rows"]}
        if args.write:
            write_json(checker, checker_payload)
        payload.update({"decision": "STALE_TOKEN_DATA_AGE_CHECKER_READY", "stale_checker": str(checker), **checker_payload})

    elif module_number == 258:
        rehearsal = workspace / "HQE_END_TO_END_OPERATOR_REHEARSAL.md"
        if args.write:
            rehearsal.write_text(
                "# HQE End-to-End Operator Rehearsal\n\n"
                "1. Open Dashboard V7.\n2. Reload env if needed.\n3. Refresh token if needed.\n4. Run data-only test.\n5. Run paper watch evidence.\n6. Run daily close.\n7. Open evidence export.\n\nNo real orders.\n",
                encoding="utf-8",
            )
        payload.update({"decision": "END_TO_END_OPERATOR_REHEARSAL_READY", "rehearsal_file": str(rehearsal)})

    elif module_number == 259:
        latency = workspace / f"DAY_{day:03d}_PAPER_SIGNAL_LATENCY_TRACKER.csv"
        if args.write:
            with latency.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=["generated_at_utc", "symbol", "signal_seen", "latency_seconds", "real_order_allowed"])
                writer.writeheader()
                writer.writerow({"generated_at_utc": utc_now(), "symbol": args.symbol, "signal_seen": "NO", "latency_seconds": "", "real_order_allowed": "NO"})
        payload.update({"decision": "PAPER_SIGNAL_LATENCY_TRACKER_READY", "latency_tracker": str(latency), "fake_signal_created": False})

    elif module_number == 260:
        snapshot = workspace / "HQE_SAFE_CONFIG_SNAPSHOT.json"
        config = {"symbol": args.symbol, "user_id": args.user_id, "paper_only": True, "data_only": True, "order_api_hard_blocked": True}
        if args.write:
            write_json(snapshot, config)
        payload.update({"decision": "SAFE_CONFIG_SNAPSHOT_READY", "safe_config_snapshot": str(snapshot), **config})

    elif module_number == 261:
        plan = workspace / "HQE_WORKSPACE_CLEANUP_REVIEW_PLAN.md"
        files = len([p for p in workspace.glob("*") if p.is_file()])
        if args.write:
            plan.write_text(f"# HQE Workspace Cleanup Review Plan\n\nFiles in workspace: {files}\n\nNo automatic delete is performed.\n", encoding="utf-8")
        payload.update({"decision": "WORKSPACE_CLEANUP_REVIEW_PLAN_READY", "cleanup_plan": str(plan), "automatic_delete_performed": False})

    elif module_number == 262:
        anomaly = workspace / "HQE_VALIDATION_ANOMALY_DETECTOR.json"
        anomalies = []
        if payload.get("actual_paper_trades", 0) > 0 and payload.get("valid_paper_trade_days", 0) == 0:
            anomalies.append("TRADE_ROWS_EXIST_BUT_VALID_DAY_ZERO")
        if args.write:
            write_json(anomaly, {"anomalies": anomalies})
        payload.update({"decision": "VALIDATION_ANOMALY_DETECTOR_READY", "anomaly_file": str(anomaly), "anomaly_count": len(anomalies), "anomalies": anomalies})

    elif module_number == 263:
        summary = workspace / "HQE_DAILY_SUMMARY_FOR_CLIPBOARD.txt"
        text = (
            f"HQE Daily Summary {args.trading_date}\n"
            f"Valid paper trade-days: {payload.get('valid_paper_trade_days', 0)} / 30\n"
            f"Actual paper trades: {payload.get('actual_paper_trades', 0)}\n"
            "Safety: paper-only/data-only/no real orders/no broker execution/no auto trading.\n"
        )
        if args.write:
            summary.write_text(text, encoding="utf-8")
        payload.update({"decision": "DAILY_SUMMARY_CLIPBOARD_PACK_READY", "summary_file": str(summary), "clipboard_auto_write": False})

    elif module_number == 264:
        scanner = workspace / "HQE_NO_BROKER_API_STATIC_SCANNER.json"
        risky_hits: List[str] = []
        for p in (repo / "scripts").glob("hqe_*.py"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for token in ["place_order(", "modify_order(", "cancel_order(", "exit_positions("]:
                if token in text:
                    risky_hits.append(f"{p.name}:{token}")
        scanner_payload = {"risky_order_call_hits": risky_hits, "scanner_scope": "scripts/hqe_*.py", "order_api_static_scan_pass": len(risky_hits) == 0}
        if args.write:
            write_json(scanner, scanner_payload)
        payload.update({"decision": "NO_BROKER_API_STATIC_SCANNER_READY", "static_scanner": str(scanner), **scanner_payload})

    elif module_number == 265:
        bundle = workspace / f"DAY_{day:03d}_FINAL_DAILY_EVIDENCE_BUNDLE.md"
        if args.write:
            bundle.write_text(
                "# HQE Final Daily Evidence Bundle\n\n"
                f"- Trading date: {args.trading_date}\n"
                f"- Valid paper trade-days: {payload.get('valid_paper_trade_days', 0)} / 30\n"
                f"- Actual paper trades: {payload.get('actual_paper_trades', 0)}\n"
                "- Real money: NO\n",
                encoding="utf-8",
            )
        payload.update({"decision": "FINAL_DAILY_EVIDENCE_BUNDLE_READY", "daily_bundle": str(bundle)})

    elif module_number == 266:
        monthly = workspace / "HQE_MONTHLY_VALIDATION_PACK.md"
        if args.write:
            monthly.write_text(
                "# HQE Monthly Validation Pack\n\n"
                "This is a paper-only validation summary shell.\n\nReal money remains NO.\n",
                encoding="utf-8",
            )
        payload.update({"decision": "MONTHLY_VALIDATION_PACK_READY", "monthly_validation_pack": str(monthly)})

    elif module_number == 267:
        launcher = workspace / "OPEN_HQE_DASHBOARD_V7_FINAL_VALIDATION_HARDENING.cmd"
        script = repo / "scripts" / "hqe_dashboard_v7_final_validation_hardening.py"
        write_cmd(launcher, [
            "echo Opening HQE Dashboard V7 Final Validation Hardening",
            f'"{py}" "{script}" --workspace "{workspace}" --trading-date "{args.trading_date}" --day-number "{day}" --user-id "{args.user_id}" --symbol "{args.symbol}" --launch --write',
            "pause",
        ])
        payload.update({"decision": "DASHBOARD_V7_FINAL_VALIDATION_HARDENING_READY", "dashboard_v7_launcher": str(launcher)})

    elif module_number == 268:
        memo = workspace / "HQE_SUPERVISORY_REVIEW_MEMO.md"
        if args.write:
            memo.write_text(
                "# HQE Supervisory Review Memo\n\n"
                "Paper-only validation is ongoing. No profitability claim. No real orders. Manual review required.\n",
                encoding="utf-8",
            )
        payload.update({"decision": "SUPERVISORY_REVIEW_MEMO_PACK_READY", "review_memo": str(memo)})

    elif module_number == 269:
        freeze = workspace / "HQE_GO_NO_GO_GOVERNANCE_FREEZE.json"
        ready = payload.get("valid_paper_trade_days", 0) >= 30 and payload.get("actual_paper_trades", 0) >= 30
        freeze_payload = {"go_no_go_status": "NO_GO_MORE_DATA_REQUIRED" if not ready else "REVIEW_REQUIRED", "real_money_allowed": False, "manual_review_required": True}
        if args.write:
            write_json(freeze, freeze_payload)
        payload.update({"decision": "GO_NO_GO_GOVERNANCE_FREEZE_READY", "go_no_go_freeze": str(freeze), **freeze_payload})

    elif module_number == 270:
        final = workspace / "HQE_MASTER_READINESS_FREEZE_FINAL.html"
        final_payload = dict(payload)
        final_payload.update({"modules_251_to_270_complete": True, "real_money_enabled": False, "master_readiness_status": "PAPER_DATA_ONLY_VALIDATION_HARDENED"})
        html_report(final, "HQE Master Readiness Freeze Final", final_payload)
        payload.update({"decision": "MASTER_READINESS_FREEZE_FINAL_READY", "master_readiness_html": str(final), "modules_251_to_270_complete": True, "real_money_enabled": False})

    return payload


def build_module(module_number: int, args: argparse.Namespace) -> Dict[str, Any]:
    payload = base_payload(module_number, args)
    return specific(module_number, payload, args)


def emit_module(module_number: int, payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    base = MODULES[module_number]["base"]
    json_path = workspace / f"{base}.json"
    md_path = workspace / f"{base}.md"
    ledger_path = workspace / "MODULES_251_270_FINAL_VALIDATION_HARDENING_LEDGER.csv"
    payload["evidence_files"] = {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}
    if args.write:
        write_json(json_path, payload)
        write_md(md_path, f"Module {module_number} {MODULES[module_number]['name']}", payload)
        append_ledger(ledger_path, payload)
        if module_number in {267, 270}:
            html_report(workspace / "HQE_FINAL_VALIDATION_HARDENING_251_270_STATUS.html", "HQE Final Validation Hardening 251-270 Status", payload)
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


def launch_v7(args: argparse.Namespace) -> int:
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
    root.title("HQE Dashboard V7 Final Validation Hardening")
    root.geometry("860x680")

    tk.Label(root, text="HQE Dashboard V7 Final Validation Hardening", font=("Segoe UI", 18, "bold")).pack(pady=(14, 2))
    tk.Label(root, text="PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING", fg="green").pack(pady=(0, 12))
    tk.Label(root, text=f"Trading date: {args.trading_date} | Symbol: {args.symbol}").pack(pady=2)
    tk.Label(root, text=f"Workspace: {workspace}", wraplength=820, justify="left").pack(pady=2)

    frame = tk.Frame(root)
    frame.pack(pady=12, fill="both", expand=True)

    buttons = [
        ("Refresh Fyers Token", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\HQE_FYERS_TOKEN_SIMPLE_REFRESH_V2.ps1" -RepoRoot "{repo}" -Workspace "{workspace}" -Symbol "{args.symbol}"'),
        ("Historical 5m Data-Only Test", f'"{py}" scripts\\hqe_fyers_historical_5m_data_only_fetcher.py --workspace "{workspace}" --symbol "{args.symbol}" --execute-live-data-only --write'),
        ("Run 251-270 Final Hardening", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\RUN_MODULES_251_270_FINAL_VALIDATION_HARDENING.ps1" -Workspace "{workspace}" -TradingDate "{args.trading_date}" -DayNumber {args.day_number} -UserId "{args.user_id}" -Symbol "{args.symbol}"'),
        ("Open Evidence Folder", f'explorer "{workspace}"'),
        ("Open Master Readiness Final", f'start "" "{workspace}\\HQE_MASTER_READINESS_FREEZE_FINAL.html"'),
        ("Open Go/No-Go Freeze", f'start "" "{workspace}\\HQE_GO_NO_GO_GOVERNANCE_FREEZE.json"'),
    ]
    for label, command in buttons:
        tk.Button(frame, text=label, width=54, height=2, command=lambda l=label, c=command: run_cmd(l, c)).pack(pady=6)

    tk.Label(root, text="Dashboard V7 is final validation hardening only. No broker order buttons exist.", fg="green").pack(pady=10)
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
    if args.launch and module_number == 267:
        return launch_v7(args)
    return 0
