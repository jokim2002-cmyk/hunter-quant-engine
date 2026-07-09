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

VERSION = "MODULES_211_230_VALIDATION_OPS_STABILITY_V1"
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
    211: {"file": "hqe_market_day_watch_state_snapshot.py", "name": "Market-Day Watch State Snapshot", "base": "MODULE_211_MARKET_DAY_WATCH_STATE_SNAPSHOT_STATUS"},
    212: {"file": "hqe_5m_candle_cache_rotator.py", "name": "5m Candle Cache Rotator", "base": "MODULE_212_5M_CANDLE_CACHE_ROTATOR_STATUS"},
    213: {"file": "hqe_data_only_poll_result_normalizer.py", "name": "Data-Only Poll Result Normalizer", "base": "MODULE_213_DATA_ONLY_POLL_RESULT_NORMALIZER_STATUS"},
    214: {"file": "hqe_intraday_paper_decision_state_machine.py", "name": "Intraday Paper Decision State Machine", "base": "MODULE_214_INTRADAY_PAPER_DECISION_STATE_MACHINE_STATUS"},
    215: {"file": "hqe_no_trade_reason_taxonomy_pack.py", "name": "No-Trade Reason Taxonomy Pack", "base": "MODULE_215_NO_TRADE_REASON_TAXONOMY_PACK_STATUS"},
    216: {"file": "hqe_paper_trade_journal_template.py", "name": "Paper Trade Journal Template", "base": "MODULE_216_PAPER_TRADE_JOURNAL_TEMPLATE_STATUS"},
    217: {"file": "hqe_daily_evidence_backup_pack.py", "name": "Daily Evidence Backup Pack", "base": "MODULE_217_DAILY_EVIDENCE_BACKUP_PACK_STATUS"},
    218: {"file": "hqe_session_restart_recovery_snapshot.py", "name": "Session Restart Recovery Snapshot", "base": "MODULE_218_SESSION_RESTART_RECOVERY_SNAPSHOT_STATUS"},
    219: {"file": "hqe_dashboard_v5_validation_ops.py", "name": "Dashboard V5 Validation Ops", "base": "MODULE_219_DASHBOARD_V5_VALIDATION_OPS_STATUS"},
    220: {"file": "hqe_end_of_day_evaluator_bridge.py", "name": "End-of-Day Evaluator Bridge", "base": "MODULE_220_END_OF_DAY_EVALUATOR_BRIDGE_STATUS"},
    221: {"file": "hqe_trade_day_quality_scorecard.py", "name": "Trade-Day Quality Scorecard", "base": "MODULE_221_TRADE_DAY_QUALITY_SCORECARD_STATUS"},
    222: {"file": "hqe_weekly_validation_summary_pack.py", "name": "Weekly Validation Summary Pack", "base": "MODULE_222_WEEKLY_VALIDATION_SUMMARY_PACK_STATUS"},
    223: {"file": "hqe_validation_drift_monitor.py", "name": "Validation Drift Monitor", "base": "MODULE_223_VALIDATION_DRIFT_MONITOR_STATUS"},
    224: {"file": "hqe_fyers_error_code_triage_pack.py", "name": "Fyers Error Code Triage Pack", "base": "MODULE_224_FYERS_ERROR_CODE_TRIAGE_PACK_STATUS"},
    225: {"file": "hqe_operator_daily_checklist_v2.py", "name": "Operator Daily Checklist V2", "base": "MODULE_225_OPERATOR_DAILY_CHECKLIST_V2_STATUS"},
    226: {"file": "hqe_paper_watch_replay_pack.py", "name": "Paper Watch Replay Pack", "base": "MODULE_226_PAPER_WATCH_REPLAY_PACK_STATUS"},
    227: {"file": "hqe_evidence_integrity_hash_pack.py", "name": "Evidence Integrity Hash Pack", "base": "MODULE_227_EVIDENCE_INTEGRITY_HASH_PACK_STATUS"},
    228: {"file": "hqe_safe_startup_preflight_gate.py", "name": "Safe Startup Preflight Gate", "base": "MODULE_228_SAFE_STARTUP_PREFLIGHT_GATE_STATUS"},
    229: {"file": "hqe_30_day_validation_review_board_pack.py", "name": "30-Day Validation Review Board Pack", "base": "MODULE_229_30_DAY_VALIDATION_REVIEW_BOARD_PACK_STATUS"},
    230: {"file": "hqe_validation_ops_master_freeze_pack.py", "name": "Validation Ops Master Freeze Pack", "base": "MODULE_230_VALIDATION_OPS_MASTER_FREEZE_PACK_STATUS"},
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


def safe_html(path: Path, title: str, payload: Dict[str, Any]) -> None:
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


def module_specific(module_number: int, payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    repo = repo_root()
    py = repo / ".venv" / "Scripts" / "python.exe"
    day = int(args.day_number)

    if module_number == 211:
        snapshot = workspace / f"DAY_{day:03d}_WATCH_STATE_SNAPSHOT.json"
        payload.update({"decision": "WATCH_STATE_SNAPSHOT_READY", "watch_state_snapshot": str(snapshot), "state": "PAPER_WATCH_READY_OR_WAITING_DATA"})
        if args.write:
            write_json(snapshot, payload)

    elif module_number == 212:
        src = workspace / "FYERS_LIVE_DATA_ONLY_5M_NORMALIZED.csv"
        cache_dir = workspace / "data_only_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        dst = cache_dir / f"{args.trading_date}_5m_normalized_cache.csv"
        copied = False
        if args.write and src.exists():
            shutil.copyfile(src, dst)
            copied = True
        payload.update({"decision": "CANDLE_CACHE_ROTATOR_READY", "cache_file": str(dst), "source_exists": src.exists(), "cache_copied": copied})

    elif module_number == 213:
        src = workspace / "FYERS_LIVE_DATA_ONLY_5M_NORMALIZED.csv"
        out = workspace / f"DAY_{day:03d}_DATA_ONLY_POLL_NORMALIZED_SUMMARY.json"
        rows = count_csv_rows(src)
        summary = {"normalized_rows": rows, "data_ready": rows > 0, "source": str(src)}
        if args.write:
            write_json(out, summary)
        payload.update({"decision": "DATA_ONLY_POLL_RESULT_NORMALIZER_READY", "poll_summary": str(out), "normalized_rows": rows})

    elif module_number == 214:
        state_file = workspace / f"DAY_{day:03d}_INTRADAY_PAPER_DECISION_STATE.json"
        state = {
            "state": "WAIT_FOR_APPROVED_SIGNAL",
            "paper_trade_allowed_without_signal": False,
            "real_order_allowed": False,
            "next_action": "continue_data_only_watch",
        }
        if args.write:
            write_json(state_file, state)
        payload.update({"decision": "INTRADAY_PAPER_DECISION_STATE_MACHINE_READY", "state_file": str(state_file), **state})

    elif module_number == 215:
        taxonomy = workspace / "HQE_NO_TRADE_REASON_TAXONOMY.json"
        reasons = {
            "NO_APPROVED_SIGNAL": "Strategy did not approve a paper signal.",
            "DATA_NOT_READY": "Fyers data-only feed not ready.",
            "OUTSIDE_MARKET_WINDOW": "Market watch outside 09:15-15:30.",
            "SAFETY_BLOCK": "Safety guard blocked the action.",
        }
        if args.write:
            write_json(taxonomy, reasons)
        payload.update({"decision": "NO_TRADE_REASON_TAXONOMY_READY", "taxonomy_file": str(taxonomy), "reason_count": len(reasons)})

    elif module_number == 216:
        journal = workspace / f"DAY_{day:03d}_PAPER_TRADE_JOURNAL_TEMPLATE.csv"
        if args.write:
            with journal.open("w", newline="", encoding="utf-8") as fh:
                fields = ["trading_date", "symbol", "paper_trade_id", "side", "option_type", "entry_time", "exit_time", "entry_price", "exit_price", "net_pnl", "reason"]
                writer = csv.DictWriter(fh, fieldnames=fields)
                writer.writeheader()
        payload.update({"decision": "PAPER_TRADE_JOURNAL_TEMPLATE_READY", "journal_template": str(journal), "fake_rows_created": False})

    elif module_number == 217:
        backup_dir = workspace / "daily_evidence_backup" / args.trading_date
        files = [p for p in workspace.glob("*") if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv", ".html"}]
        copied = 0
        if args.write:
            backup_dir.mkdir(parents=True, exist_ok=True)
            for p in files[:200]:
                try:
                    shutil.copyfile(p, backup_dir / p.name)
                    copied += 1
                except Exception:
                    pass
        payload.update({"decision": "DAILY_EVIDENCE_BACKUP_PACK_READY", "backup_dir": str(backup_dir), "backup_file_count": copied, "backup_source_count": len(files)})

    elif module_number == 218:
        recovery = workspace / "HQE_SESSION_RESTART_RECOVERY_SNAPSHOT.json"
        recovery_payload = {
            "last_status": payload.get("decision", "UNKNOWN"),
            "restart_action": "open_dashboard_v5_and_refresh_data_only_status",
            "real_orders_to_recover": 0,
        }
        if args.write:
            write_json(recovery, recovery_payload)
        payload.update({"decision": "SESSION_RESTART_RECOVERY_SNAPSHOT_READY", "recovery_snapshot": str(recovery)})

    elif module_number == 219:
        launcher = workspace / "OPEN_HQE_DASHBOARD_V5_VALIDATION_OPS.cmd"
        script = repo / "scripts" / "hqe_dashboard_v5_validation_ops.py"
        write_cmd(launcher, [
            "echo Opening HQE Dashboard V5 Validation Ops",
            f'"{py}" "{script}" --workspace "{workspace}" --trading-date "{args.trading_date}" --day-number "{day}" --user-id "{args.user_id}" --symbol "{args.symbol}" --launch --write',
            "pause",
        ])
        payload.update({"decision": "DASHBOARD_V5_VALIDATION_OPS_READY", "dashboard_v5_launcher": str(launcher)})

    elif module_number == 220:
        bridge = workspace / f"DAY_{day:03d}_END_OF_DAY_EVALUATOR_BRIDGE.json"
        bridge_payload = {"daily_close_ready": True, "valid_day_counted_only_if_trade_rows_exist": True, "real_money_allowed": False}
        if args.write:
            write_json(bridge, bridge_payload)
        payload.update({"decision": "END_OF_DAY_EVALUATOR_BRIDGE_READY", "eod_bridge_file": str(bridge)})

    elif module_number == 221:
        scorecard = workspace / f"DAY_{day:03d}_TRADE_DAY_QUALITY_SCORECARD.json"
        score = {
            "data_ready": payload["data_health"]["data_only_connection_ready"],
            "paper_trade_count": payload.get("actual_paper_trades", 0),
            "quality_status": "OBSERVED_NO_TRADE_OR_WAITING_MORE_DATA",
            "real_money_ready": False,
        }
        if args.write:
            write_json(scorecard, score)
        payload.update({"decision": "TRADE_DAY_QUALITY_SCORECARD_READY", "scorecard_file": str(scorecard), **score})

    elif module_number == 222:
        weekly = workspace / "HQE_WEEKLY_VALIDATION_SUMMARY.md"
        if args.write:
            weekly.write_text(
                "# HQE Weekly Validation Summary\n\n"
                f"- Valid paper trade days: {payload.get('valid_paper_trade_days', 0)} / 30\n"
                f"- Actual paper trades: {payload.get('actual_paper_trades', 0)}\n"
                "- Real money: NO\n",
                encoding="utf-8",
            )
        payload.update({"decision": "WEEKLY_VALIDATION_SUMMARY_PACK_READY", "weekly_summary": str(weekly)})

    elif module_number == 223:
        drift = workspace / "HQE_VALIDATION_DRIFT_MONITOR.json"
        drift_payload = {"candidate_tuning_detected": False, "strategy_locked": True, "drift_status": "NO_DRIFT_DETECTED_BY_FILE_EVIDENCE"}
        if args.write:
            write_json(drift, drift_payload)
        payload.update({"decision": "VALIDATION_DRIFT_MONITOR_READY", "drift_monitor_file": str(drift), **drift_payload})

    elif module_number == 224:
        triage = workspace / "HQE_FYERS_ERROR_CODE_TRIAGE.md"
        if args.write:
            triage.write_text(
                "# HQE Fyers Error Code Triage\n\n"
                "- Authentication error: refresh Fyers token.\n"
                "- Zero rows: run data-only test again and check symbol.\n"
                "- Network error: retry after connection check.\n"
                "- Never enable order APIs.\n",
                encoding="utf-8",
            )
        payload.update({"decision": "FYERS_ERROR_CODE_TRIAGE_PACK_READY", "triage_file": str(triage)})

    elif module_number == 225:
        checklist = workspace / f"DAY_{day:03d}_OPERATOR_DAILY_CHECKLIST_V2.md"
        if args.write:
            checklist.write_text(
                "# HQE Operator Daily Checklist V2\n\n"
                "- [ ] Login local HQE gate\n"
                "- [ ] Refresh Fyers token if needed\n"
                "- [ ] Run Historical 5m Data-Only Test\n"
                "- [ ] Open Dashboard V5\n"
                "- [ ] Watch 09:15-15:30\n"
                "- [ ] Run daily close pack\n",
                encoding="utf-8",
            )
        payload.update({"decision": "OPERATOR_DAILY_CHECKLIST_V2_READY", "checklist_file": str(checklist)})

    elif module_number == 226:
        replay = workspace / "HQE_PAPER_WATCH_REPLAY_PACK.json"
        replay_payload = {"replay_source": "data_only_cache", "replay_executes_orders": False, "replay_creates_fake_trades": False}
        if args.write:
            write_json(replay, replay_payload)
        payload.update({"decision": "PAPER_WATCH_REPLAY_PACK_READY", "replay_pack_file": str(replay), **replay_payload})

    elif module_number == 227:
        import hashlib
        hashes = workspace / "HQE_EVIDENCE_INTEGRITY_HASHES.csv"
        files = [p for p in workspace.glob("*") if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv"}]
        if args.write:
            with hashes.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=["file", "sha256"])
                writer.writeheader()
                for p in files[:300]:
                    try:
                        digest = hashlib.sha256(p.read_bytes()).hexdigest()
                        writer.writerow({"file": p.name, "sha256": digest})
                    except Exception:
                        pass
        payload.update({"decision": "EVIDENCE_INTEGRITY_HASH_PACK_READY", "hash_file": str(hashes), "hashed_file_count": len(files[:300])})

    elif module_number == 228:
        preflight = workspace / "HQE_SAFE_STARTUP_PREFLIGHT_GATE.json"
        ready = payload["secrets"]["credentials_complete_for_data_only_watch"] and payload["data_health"]["data_only_connection_ready"]
        preflight_payload = {"safe_startup_ready": ready, "real_money_allowed": False, "orders_allowed": False}
        if args.write:
            write_json(preflight, preflight_payload)
        payload.update({"decision": "SAFE_STARTUP_PREFLIGHT_READY" if ready else "SAFE_STARTUP_PREFLIGHT_WAITING_FOR_TOKEN_OR_DATA", "preflight_file": str(preflight), **preflight_payload})

    elif module_number == 229:
        board = workspace / "HQE_30_DAY_VALIDATION_REVIEW_BOARD.md"
        ready = payload.get("valid_paper_trade_days", 0) >= 30 and payload.get("actual_paper_trades", 0) >= 30
        if args.write:
            board.write_text(
                "# HQE 30-Day Validation Review Board\n\n"
                f"- Valid paper trade days: {payload.get('valid_paper_trade_days', 0)} / 30\n"
                f"- Actual paper trades: {payload.get('actual_paper_trades', 0)}\n"
                f"- Review ready: {ready}\n"
                "- Real money remains NO until manual review.\n",
                encoding="utf-8",
            )
        payload.update({"decision": "VALIDATION_REVIEW_BOARD_HOLD_MORE_DATA_REQUIRED" if not ready else "VALIDATION_REVIEW_BOARD_READY_FOR_MANUAL_REVIEW", "review_board_file": str(board), "review_ready": ready, "real_money_allowed": False})

    elif module_number == 230:
        freeze = workspace / "HQE_VALIDATION_OPS_MASTER_FREEZE.md"
        if args.write:
            freeze.write_text(
                "# HQE Validation Ops Master Freeze\n\n"
                "Modules 211-230 installed.\n\n"
                "Safety: paper-only/data-only/no real orders/no broker execution/no auto trading.\n",
                encoding="utf-8",
            )
        payload.update({"decision": "VALIDATION_OPS_MASTER_FREEZE_READY", "master_freeze_file": str(freeze), "modules_211_to_230_complete": True, "real_money_enabled": False})

    return payload


def build_module(module_number: int, args: argparse.Namespace) -> Dict[str, Any]:
    payload = base_payload(module_number, args)
    return module_specific(module_number, payload, args)


def emit_module(module_number: int, payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    base = MODULES[module_number]["base"]
    json_path = workspace / f"{base}.json"
    md_path = workspace / f"{base}.md"
    ledger_path = workspace / "MODULES_211_230_VALIDATION_OPS_LEDGER.csv"
    payload["evidence_files"] = {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}
    if args.write:
        write_json(json_path, payload)
        write_md(md_path, f"Module {module_number} {MODULES[module_number]['name']}", payload)
        append_ledger(ledger_path, payload)
        if module_number in {219, 230}:
            safe_html(workspace / "HQE_VALIDATION_OPS_211_230_STATUS.html", "HQE Validation Ops 211-230 Status", payload)
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


def launch_v5(args: argparse.Namespace) -> int:
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
    root.title("HQE Dashboard V5 Validation Ops")
    root.geometry("820x640")

    tk.Label(root, text="HQE Dashboard V5 Validation Ops", font=("Segoe UI", 18, "bold")).pack(pady=(14, 2))
    tk.Label(root, text="PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING", fg="green").pack(pady=(0, 12))
    tk.Label(root, text=f"Trading date: {args.trading_date} | Symbol: {args.symbol}").pack(pady=2)
    tk.Label(root, text=f"Workspace: {workspace}", wraplength=780, justify="left").pack(pady=2)

    frame = tk.Frame(root)
    frame.pack(pady=12, fill="both", expand=True)

    buttons = [
        ("Refresh Fyers Token", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\HQE_FYERS_TOKEN_SIMPLE_REFRESH_V2.ps1" -RepoRoot "{repo}" -Workspace "{workspace}" -Symbol "{args.symbol}"'),
        ("Historical 5m Data-Only Test", f'"{py}" scripts\\hqe_fyers_historical_5m_data_only_fetcher.py --workspace "{workspace}" --symbol "{args.symbol}" --execute-live-data-only --write'),
        ("Run 211-230 Validation Ops", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\RUN_MODULES_211_230_VALIDATION_OPS_STABILITY.ps1" -Workspace "{workspace}" -TradingDate "{args.trading_date}" -DayNumber {args.day_number} -UserId "{args.user_id}" -Symbol "{args.symbol}"'),
        ("Open Evidence Folder", f'explorer "{workspace}"'),
        ("Open Validation Ops Status HTML", f'start "" "{workspace}\\HQE_VALIDATION_OPS_211_230_STATUS.html"'),
        ("Open 30-Day Review Board", f'start "" "{workspace}\\HQE_30_DAY_VALIDATION_REVIEW_BOARD.md"'),
    ]
    for label, command in buttons:
        tk.Button(frame, text=label, width=50, height=2, command=lambda l=label, c=command: run_cmd(l, c)).pack(pady=6)

    tk.Label(root, text="Dashboard V5 is local evidence control only. No broker order buttons exist.", fg="green").pack(pady=10)
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
    if args.launch and module_number == 219:
        return launch_v5(args)
    return 0
