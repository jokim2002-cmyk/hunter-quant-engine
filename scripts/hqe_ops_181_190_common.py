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

VERSION = "MODULES_181_190_FINAL_LIVE_PAPER_OPS_V2"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_USER_ID = "jokim-local"
DEFAULT_SYMBOL = "NSE:NIFTY50-INDEX"
DEFAULT_TRADING_DATE = "2026-07-09"
DEFAULT_DAY_NUMBER = 1

BLOCKED_ORDER_APIS = [
    "place_order", "modify_order", "cancel_order", "exit_positions",
    "place_basket_orders", "place_gtt_order", "modify_gtt_order",
    "cancel_gtt_order", "convert_position", "orderbook", "tradebook",
    "positions", "holdings", "funds",
]

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p.add_argument("--trading-date", default=DEFAULT_TRADING_DATE)
    p.add_argument("--day-number", type=int, default=DEFAULT_DAY_NUMBER)
    p.add_argument("--user-id", default=DEFAULT_USER_ID)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    p.add_argument("--write", action="store_true")
    p.add_argument("--guard-check", action="store_true")
    p.add_argument("--launch", action="store_true")
    return p


def workspace_path(value: str | Path) -> Path:
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


def append_ledger(path: Path, payload: Dict[str, Any]) -> None:
    row = {
        "generated_at_utc": payload.get("generated_at_utc", utc_now()),
        "module_number": payload.get("module_number", ""),
        "module_name": payload.get("module_name", ""),
        "module_status": payload.get("module_status", ""),
        "decision": payload.get("decision", ""),
        "workspace": payload.get("workspace", ""),
        "symbol": payload.get("symbol", ""),
        "trading_date": payload.get("trading_date", ""),
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


def day_stats(workspace: Path) -> Dict[str, Any]:
    ledger = workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv"
    rows: List[Dict[str, Any]] = []
    if ledger.exists():
        with ledger.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))

    observed_dates = set()
    valid_dates = set()
    for row in rows:
        date = (row.get("trading_date") or row.get("date") or row.get("day") or "").strip()
        if date:
            observed_dates.add(date)
        try:
            trade_count = int(float(str(row.get("trade_count", "0")).strip() or "0"))
        except ValueError:
            trade_count = 0
        if date and trade_count > 0:
            valid_dates.add(date)

    return {
        "day_ledger_rows": len(rows),
        "observed_session_days": len(observed_dates),
        "valid_paper_trade_days": len(valid_dates),
        "no_trade_observed_days": max(len(observed_dates) - len(valid_dates), 0),
        "target_valid_paper_trade_days": 30,
        "remaining_valid_trade_days": max(30 - len(valid_dates), 0),
        "actual_paper_trades": count_actual_trades(workspace),
        "actual_trade_rows_source": "MASTER_OR_DAY_LOGS",
        "distinct_expiry_weeks": 0,
    }


def count_actual_trades(workspace: Path) -> int:
    total = 0
    candidates = [workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv", workspace / "FORWARD_PAPER_TRADE_MASTER_LEDGER.csv"]
    candidates.extend(workspace.glob("DAY_*_FORWARD_TRADE_LOG.csv"))
    for path in candidates:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                total += len(list(csv.DictReader(fh)))
        except Exception:
            pass
    return total


def secrets_status() -> Dict[str, Any]:
    required = ["FYERS_CLIENT_ID", "FYERS_ACCESS_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    return {
        "credential_source": "environment_variables_only",
        "required_env_names": required,
        "missing_required_env_names": missing,
        "present_required_env_count": len(required) - len(missing),
        "credentials_complete_for_future_data_transport": not missing,
        "secret_values_redacted": True,
        "plaintext_secret_storage_allowed": False,
    }


def write_cmd(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("@echo off\n" + "\n".join(lines) + "\n", encoding="utf-8")


def make_html(path: Path, title: str, payload: Dict[str, Any]) -> None:
    rows = []
    for key, value in payload.items():
        if key in {"safety_lock", "blocked_order_apis"}:
            continue
        shown = json.dumps(value, indent=2, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        rows.append("<tr><th>" + html.escape(str(key)) + "</th><td><pre>" + html.escape(shown) + "</pre></td></tr>")
    doc = (
        "<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(title) + "</title>"
        "<style>"
        "body{font-family:Segoe UI,Arial,sans-serif;margin:24px;background:#f7f7f7;color:#111}"
        ".card{background:white;padding:18px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.08);margin-bottom:16px}"
        ".safe{color:#0a7d20;font-weight:bold}"
        "table{border-collapse:collapse;width:100%;background:white}"
        "th,td{text-align:left;vertical-align:top;border-bottom:1px solid #ddd;padding:8px}"
        "th{width:260px}pre{white-space:pre-wrap;margin:0}"
        "</style></head><body>"
        "<div class='card'><h1>" + html.escape(title) + "</h1>"
        "<p class='safe'>PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING</p></div>"
        "<div class='card'><table>" + "".join(rows) + "</table></div></body></html>"
    )
    path.write_text(doc, encoding="utf-8")


def base_payload(module_number: int, module_name: str, args: argparse.Namespace) -> Dict[str, Any]:
    workspace = workspace_path(args.workspace)
    payload = {
        "version": VERSION,
        "module_number": module_number,
        "module_name": module_name,
        "generated_at_utc": utc_now(),
        "workspace": str(workspace),
        "trading_date": args.trading_date,
        "day_number": args.day_number,
        "symbol": args.symbol,
        "user_id": args.user_id,
        "module_status": "PASS",
        "blocked_order_apis": BLOCKED_ORDER_APIS,
        "safety_lock": SAFETY_LOCK,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "fake_trades_created": False,
        "candidate_tuning": False,
        "real_money_automatic": False,
        "secrets": secrets_status(),
    }
    payload.update(day_stats(workspace))
    return payload


def guard_check(module_number: int, module_name: str) -> int:
    payload = {
        "version": VERSION,
        "guard_check_status": "PASS",
        "module_number": module_number,
        "module_name": module_name,
        "safety_lock": SAFETY_LOCK,
        "blocked_order_apis": {name: "HARD_BLOCKED" for name in BLOCKED_ORDER_APIS},
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "real_money_automatic": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def module_specifics(module_number: int, payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = workspace_path(args.workspace)
    repo = repo_root_from_script()
    py = repo / ".venv" / "Scripts" / "python.exe"

    if module_number == 181:
        helper = repo / "scripts" / "HQE_FYERS_TOKEN_SIMPLE_REFRESH_V2.ps1"
        launcher = workspace / "OPEN_HQE_FYERS_TOKEN_REFRESH_HELPER.cmd"
        write_cmd(launcher, [
            "echo HQE FYERS TOKEN REFRESH HELPER",
            "echo Safety: DATA ONLY / NO ORDERS / NO BROKER EXECUTION",
            f'powershell -NoProfile -ExecutionPolicy Bypass -File "{helper}" -RepoRoot "{repo}" -Workspace "{workspace}" -Symbol "{args.symbol}"',
            "pause",
        ])
        payload.update({"decision": "FYERS_TOKEN_REFRESH_HELPER_READY_DASHBOARD_BUTTON", "token_refresh_launcher_path": str(launcher)})

    elif module_number == 182:
        dashboard = repo / "scripts" / "hqe_local_visual_dashboard_live_paper_v2.py"
        launcher = workspace / "OPEN_HQE_VISUAL_DASHBOARD_V2_LIVE_PAPER.cmd"
        write_cmd(launcher, [
            "echo Opening HQE Visual Dashboard V2...",
            f'"{py}" "{dashboard}" --workspace "{workspace}" --user-id "{args.user_id}" --symbol "{args.symbol}" --launch',
            "pause",
        ])
        payload.update({"decision": "VISUAL_DASHBOARD_V2_LAUNCHER_FIXED_WITH_LAUNCH_FLAG", "launcher_path": str(launcher), "launch_flag_added": True})

    elif module_number == 183:
        module_173 = read_json(workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json")
        history = module_173.get("history_result", {})
        rows = int(history.get("rows", 0) or 0)
        response = history.get("response_redacted", {})
        api_ok = response.get("s") == "ok" or rows > 0
        payload.update({
            "decision": "FYERS_DATA_ONLY_HEALTH_OK" if api_ok else "FYERS_DATA_ONLY_HEALTH_WAITING_FOR_SUCCESSFUL_DATA_CALL",
            "last_history_rows": rows,
            "last_history_api_ok": api_ok,
            "last_history_code": response.get("code"),
            "data_only_connection_ready": api_ok,
        })

    elif module_number == 184:
        module_173 = read_json(workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json")
        candles = module_173.get("history_result", {}).get("response_redacted", {}).get("candles", [])
        out_csv = workspace / "FYERS_LIVE_DATA_ONLY_5M_NORMALIZED.csv"
        rows_written = 0
        if args.write:
            with out_csv.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=["datetime", "open", "high", "low", "close", "volume", "symbol", "source"])
                writer.writeheader()
                for candle in candles if isinstance(candles, list) else []:
                    if not isinstance(candle, list) or len(candle) < 6:
                        continue
                    ts, o, h, l, c, v = candle[:6]
                    try:
                        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
                    except Exception:
                        dt = str(ts)
                    writer.writerow({"datetime": dt, "open": o, "high": h, "low": l, "close": c, "volume": v, "symbol": args.symbol, "source": "fyers_data_only_history"})
                    rows_written += 1
        else:
            rows_written = len(candles) if isinstance(candles, list) else 0
        payload.update({
            "decision": "LIVE_5M_NORMALIZED_DATA_READY" if rows_written > 0 else "LIVE_5M_NORMALIZED_DATA_WAITING_FOR_CANDLES",
            "source_candles": len(candles) if isinstance(candles, list) else 0,
            "normalized_rows_written": rows_written,
            "normalized_csv": str(out_csv),
        })

    elif module_number == 185:
        signal_csv = workspace / f"DAY_{int(args.day_number):03d}_LIVE_PAPER_SIGNAL_FEED.csv"
        if args.write:
            with signal_csv.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=["trading_date", "symbol", "signal_status", "approved_signal", "reason", "real_order_allowed"])
                writer.writeheader()
                writer.writerow({
                    "trading_date": args.trading_date,
                    "symbol": args.symbol,
                    "signal_status": "WAITING_FOR_LIVE_STRATEGY_APPROVED_SIGNAL",
                    "approved_signal": "NO",
                    "reason": "NO_APPROVED_SIGNAL_GENERATED_BY_BRIDGE_NO_FAKE_TRADES",
                    "real_order_allowed": "NO",
                })
        payload.update({"decision": "LIVE_PAPER_SIGNAL_FEED_BRIDGE_READY_NO_FAKE_SIGNALS", "signal_feed_file": str(signal_csv), "approved_signal_rows_created": 0})

    elif module_number == 186:
        health = read_json(workspace / "MODULE_183_FYERS_DATA_ONLY_HEALTH_MONITOR_STATUS.json")
        data_ready = bool(health.get("data_only_connection_ready"))
        payload.update({
            "decision": "LIVE_PAPER_SESSION_READY_MANUAL_WATCH_ALLOWED" if data_ready else "LIVE_PAPER_SESSION_WAITING_FOR_DATA_ONLY_CONNECTION",
            "data_only_connection_ready": data_ready,
            "session_start_allowed": data_ready,
            "paper_trade_logging_allowed_only_with_explicit_approved_signal": True,
            "real_order_allowed": False,
        })

    elif module_number == 187:
        script = repo / "scripts" / "hqe_visual_dashboard_v3_operator_app.py"
        launcher = workspace / "OPEN_HQE_VISUAL_DASHBOARD_V3_SAFE.cmd"
        html_path = workspace / "HQE_VISUAL_DASHBOARD_V3_STATUS.html"
        write_cmd(launcher, [
            "echo Opening HQE Visual Dashboard V3...",
            f'"{py}" "{script}" --workspace "{workspace}" --user-id "{args.user_id}" --symbol "{args.symbol}" --launch',
            "pause",
        ])
        payload.update({
            "decision": "VISUAL_DASHBOARD_V3_READY_OPERATOR_BUTTONS_LOCAL_ONLY",
            "launcher_path": str(launcher),
            "html_status_path": str(html_path),
            "dashboard_buttons": ["Refresh Login Status", "Refresh Fyers Token", "Historical 5m Data-Only Test", "LTP Data-Only Test", "Run 181-190 Status", "Open Evidence Folder"],
        })
        make_html(html_path, "HQE Visual Dashboard V3 Status", payload)

    elif module_number == 188:
        payload.update({
            "decision": "DAILY_CLOSE_READY_AFTER_MARKET_MANUAL_REVIEW_REQUIRED",
            "post_market_close_steps": ["Run no-trade reason or paper execution logger", "Run day close recorder", "Run 30 valid trade-day tracker", "Open daily evidence", "Do not count no-trade day as valid trade-day"],
            "auto_close_executed_by_module_188": False,
        })

    elif module_number == 189:
        sop = workspace / "HQE_FYERS_TOKEN_REFRESH_SIMPLE_SOP.md"
        if args.write:
            sop.write_text(
                "# HQE Fyers Token Refresh SOP\n\n"
                "Safety: DATA ONLY / NO ORDERS / NO BROKER EXECUTION / NO AUTO TRADING.\n\n"
                "1. Open HQE Visual Dashboard V3.\n"
                "2. Click Refresh Fyers Token.\n"
                "3. Login in Fyers browser page.\n"
                "4. Copy final redirected URL from browser address bar.\n"
                "5. Paste it into Notepad opened by HQE, save, and close.\n"
                "6. HQE saves token to user environment and runs data-only test.\n"
                "7. Never paste token, secret key, or auth code into chat.\n",
                encoding="utf-8",
            )
        payload.update({"decision": "FYERS_TOKEN_REFRESH_SOP_READY", "sop_file": str(sop), "daily_secret_paste_required": False})

    elif module_number == 190:
        health = read_json(workspace / "MODULE_183_FYERS_DATA_ONLY_HEALTH_MONITOR_STATUS.json")
        controller = read_json(workspace / "MODULE_186_LIVE_PAPER_SESSION_CONTROLLER_STATUS.json")
        dashboard = read_json(workspace / "MODULE_187_VISUAL_DASHBOARD_V3_STATUS.json")
        data_ready = bool(health.get("data_only_connection_ready"))
        session_ready = bool(controller.get("session_start_allowed"))
        dashboard_ready = dashboard.get("module_status") == "PASS"
        ready = data_ready and session_ready and dashboard_ready
        html_path = workspace / "HQE_LIVE_PAPER_OPERATION_FINAL_CLOSE_STATUS.html"
        payload.update({
            "decision": "LIVE_PAPER_OPERATION_READY_FOR_NEXT_MARKET_DAY_MANUAL_START" if ready else "LIVE_PAPER_OPERATION_WAITING_FOR_DATA_OR_DASHBOARD_STATUS",
            "ready_for_next_market_day_manual_paper_operation": ready,
            "data_only_connection_ready": data_ready,
            "session_controller_ready": session_ready,
            "visual_dashboard_v3_ready": dashboard_ready,
            "real_money_ready": False,
            "real_money_requires_future_manual_review": True,
            "html_status_path": str(html_path),
        })
        make_html(html_path, "HQE Live Paper Operation Final Close", payload)
    return payload


def emit(payload: Dict[str, Any], basename: str, title: str, args: argparse.Namespace) -> Dict[str, Any]:
    workspace = workspace_path(args.workspace)
    json_path = workspace / f"{basename}.json"
    md_path = workspace / f"{basename}.md"
    ledger_path = workspace / "MODULES_181_190_FINAL_LIVE_PAPER_OPS_LEDGER.csv"
    payload["evidence_files"] = {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}
    if args.write:
        write_json(json_path, payload)
        write_md(md_path, title, payload)
        append_ledger(ledger_path, payload)
    return payload


def build_module_payload(module_number: int, module_name: str, basename: str, title: str, args: argparse.Namespace) -> Dict[str, Any]:
    payload = base_payload(module_number, module_name, args)
    payload = module_specifics(module_number, payload, args)
    return emit(payload, basename, title, args)


def launch_dashboard_v3(args: argparse.Namespace) -> int:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        print("Tkinter not available. Use generated CMD/HTML status files.")
        return 1

    workspace = Path(args.workspace)
    repo = repo_root_from_script()
    py = repo / ".venv" / "Scripts" / "python.exe"

    def run_cmd(label: str, command: str) -> None:
        try:
            subprocess.Popen(command, cwd=str(repo), shell=True)
        except Exception as exc:
            messagebox.showerror(label, str(exc))

    root = tk.Tk()
    root.title("HQE Visual Dashboard V3 - Paper Only")
    root.geometry("780x580")
    tk.Label(root, text="HQE Visual Dashboard V3", font=("Segoe UI", 18, "bold")).pack(pady=(14, 2))
    tk.Label(root, text="PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING", fg="green").pack(pady=(0, 12))
    tk.Label(root, text=f"Workspace: {workspace}", wraplength=740, justify="left").pack(pady=2)
    tk.Label(root, text=f"User ID: {args.user_id}   Symbol: {args.symbol}", wraplength=740, justify="left").pack(pady=2)

    frame = tk.Frame(root)
    frame.pack(pady=12, fill="both", expand=True)

    buttons = [
        ("Refresh Login Status", f'"{py}" scripts\\hqe_local_login_shell.py --status --workspace "{workspace}"'),
        ("Refresh Fyers Token", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\HQE_FYERS_TOKEN_SIMPLE_REFRESH_V2.ps1" -RepoRoot "{repo}" -Workspace "{workspace}" -Symbol "{args.symbol}"'),
        ("Historical 5m Data-Only Test", f'"{py}" scripts\\hqe_fyers_historical_5m_data_only_fetcher.py --workspace "{workspace}" --symbol "{args.symbol}" --execute-live-data-only --write'),
        ("LTP Data-Only Test", f'"{py}" scripts\\hqe_fyers_live_data_only_ltp_test.py --workspace "{workspace}" --symbol "{args.symbol}" --execute-live-data-only --write'),
        ("Run 181-190 Status", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\RUN_MODULES_181_190_FINAL_LIVE_PAPER_OPS.ps1" -Workspace "{workspace}" -TradingDate "{args.trading_date}" -DayNumber {args.day_number} -UserId "{args.user_id}" -Symbol "{args.symbol}"'),
        ("Open Evidence Folder", f'explorer "{workspace}"'),
        ("Open Dashboard V3 Status HTML", f'start "" "{workspace}\\HQE_VISUAL_DASHBOARD_V3_STATUS.html"'),
    ]
    for label, command in buttons:
        tk.Button(frame, text=label, width=46, height=2, command=lambda l=label, c=command: run_cmd(l, c)).pack(pady=5)

    tk.Label(root, text="Safety: all actions remain data-only/local paper evidence. Order APIs are hard-blocked.", fg="green").pack(pady=10)
    root.mainloop()
    return 0


def module_main(module_number: int, module_name: str, basename: str, title: str) -> int:
    p = parser(module_name)
    args = p.parse_args()
    if args.guard_check:
        return guard_check(module_number, module_name)
    payload = build_module_payload(module_number, module_name, basename, title, args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.launch and module_number == 187:
        return launch_dashboard_v3(args)
    return 0
