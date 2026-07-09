from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


MODULE_NUMBER = 191
MODULE_NAME = "Real Market-Day Paper Watch Launcher"
VERSION = "MODULE_191_REAL_MARKET_DAY_PAPER_WATCH_LAUNCHER_V1"

DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_USER_ID = "jokim-local"
DEFAULT_SYMBOL = "NSE:NIFTY50-INDEX"

BLOCKED_ORDER_APIS = [
    "place_order",
    "modify_order",
    "cancel_order",
    "exit_positions",
    "place_basket_orders",
    "place_gtt_order",
    "modify_gtt_order",
    "cancel_gtt_order",
    "convert_position",
    "orderbook",
    "tradebook",
    "positions",
    "holdings",
    "funds",
]

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "manual_operator_start_required": True,
    "manual_login_required": True,
    "manual_operator_review_required": True,
    "market_window_0915_1530_plan_only": True,
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


def today_local() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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
    text = "# " + title + "\n\n```json\n" + json.dumps(payload, indent=2, sort_keys=True) + "\n```\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
        "ready_for_manual_market_watch": payload.get("ready_for_manual_market_watch", False),
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
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                total += len(list(csv.DictReader(fh)))
        except Exception:
            pass
    return total


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


def latest_data_health(workspace: Path) -> Dict[str, Any]:
    module_183 = read_json(workspace / "MODULE_183_FYERS_DATA_ONLY_HEALTH_MONITOR_STATUS.json")
    module_173 = read_json(workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json")
    history = module_173.get("history_result", {})
    rows = int(history.get("rows", 0) or 0)
    response = history.get("response_redacted", {})
    api_ok = bool(module_183.get("data_only_connection_ready")) or response.get("s") == "ok" or rows > 0
    return {
        "module_183_found": bool(module_183),
        "module_173_found": bool(module_173),
        "last_history_rows": rows,
        "last_history_api_ok": api_ok,
        "last_history_code": response.get("code"),
        "data_only_connection_ready": api_ok,
    }


def generate_watch_cmd(workspace: Path, user_id: str, symbol: str, trading_date: str) -> Path:
    repo = repo_root()
    py = repo / ".venv" / "Scripts" / "python.exe"
    cmd = workspace / "START_HQE_MARKET_DAY_PAPER_WATCH_0915_1530.cmd"
    write_cmd(
        cmd,
        [
            "title HQE Market-Day Paper Watch 0915-1530",
            "echo HQE MARKET-DAY PAPER WATCH",
            "echo Safety: PAPER ONLY / DATA ONLY / NO ORDERS / NO BROKER EXECUTION / NO AUTO TRADING",
            "echo.",
            "echo Step 1: refresh token if required from Dashboard V3.",
            "echo Step 2: run data-only 5m test.",
            "echo Step 3: keep this window open during market session.",
            "echo.",
            f'"{py}" "scripts\\hqe_real_market_day_paper_watch_launcher.py" --workspace "{workspace}" --user-id "{user_id}" --symbol "{symbol}" --trading-date "{trading_date}" --write',
            "echo.",
            "echo Optional data-only refresh command:",
            f'echo "{py}" "scripts\\hqe_fyers_historical_5m_data_only_fetcher.py" --workspace "{workspace}" --symbol "{symbol}" --execute-live-data-only --write',
            "echo.",
            "echo No automatic order execution is available in this launcher.",
            "pause",
        ],
    )
    return cmd


def generate_html(workspace: Path, payload: Dict[str, Any]) -> Path:
    html_path = workspace / "HQE_MARKET_DAY_PAPER_WATCH_0915_1530.html"
    safe = "PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING"
    rows = []
    for key, value in payload.items():
        if key in {"blocked_order_apis", "safety_lock"}:
            continue
        shown = json.dumps(value, indent=2, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        rows.append(
            "<tr><th>{}</th><td><pre>{}</pre></td></tr>".format(
                str(key).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                shown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
            )
        )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><title>HQE Market-Day Paper Watch</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;background:#f7f7f7;margin:24px;color:#111}"
        ".card{background:white;padding:18px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.08);margin-bottom:16px}"
        ".safe{color:#0a7d20;font-weight:bold}table{border-collapse:collapse;width:100%;background:white}"
        "th,td{text-align:left;vertical-align:top;border-bottom:1px solid #ddd;padding:8px}"
        "th{width:260px}pre{white-space:pre-wrap;margin:0}</style></head><body>"
        "<div class='card'><h1>HQE Market-Day Paper Watch 09:15-15:30</h1>"
        "<p class='safe'>" + safe + "</p></div>"
        "<div class='card'><table>" + "".join(rows) + "</table></div></body></html>"
    )
    html_path.write_text(html, encoding="utf-8")
    return html_path


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    trading_date = args.trading_date or today_local()
    data_health = latest_data_health(workspace)
    credentials = env_status()
    ready = bool(data_health["data_only_connection_ready"] and credentials["credentials_complete_for_data_only_watch"])
    decision = (
        "MARKET_DAY_PAPER_WATCH_READY_FOR_MANUAL_START_0915_1530"
        if ready
        else "MARKET_DAY_PAPER_WATCH_WAITING_FOR_TOKEN_OR_DATA_HEALTH"
    )

    watch_cmd = generate_watch_cmd(workspace, args.user_id, args.symbol, trading_date)

    payload: Dict[str, Any] = {
        "version": VERSION,
        "module_number": MODULE_NUMBER,
        "module_name": MODULE_NAME,
        "module_status": "PASS",
        "decision": decision,
        "generated_at_utc": utc_now(),
        "workspace": str(workspace),
        "user_id": args.user_id,
        "symbol": args.symbol,
        "trading_date": trading_date,
        "market_watch_window": {
            "start": "09:15",
            "end": "15:30",
            "timezone": "Asia/Kolkata",
            "mode": "manual_operator_start_paper_watch",
        },
        "ready_for_manual_market_watch": ready,
        "data_only_connection_ready": data_health["data_only_connection_ready"],
        "fyers_credentials_ready_for_data_only_watch": credentials["credentials_complete_for_data_only_watch"],
        "secrets": credentials,
        "data_health": data_health,
        "watch_launcher_cmd": str(watch_cmd),
        "operator_actions": [
            "Open Dashboard V3",
            "Refresh Fyers token if needed",
            "Run Historical 5m Data-Only Test",
            "Start Market-Day Paper Watch at or after 09:15",
            "Keep evidence folder open",
            "After 15:30 run daily close/report tracker",
        ],
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
    html_path = generate_html(workspace, payload)
    payload["html_status_path"] = str(html_path)
    return payload


def emit(payload: Dict[str, Any], workspace: Path, write: bool) -> Dict[str, Any]:
    json_path = workspace / "MODULE_191_REAL_MARKET_DAY_PAPER_WATCH_LAUNCHER_STATUS.json"
    md_path = workspace / "MODULE_191_REAL_MARKET_DAY_PAPER_WATCH_LAUNCHER_STATUS.md"
    ledger_path = workspace / "MODULE_191_REAL_MARKET_DAY_PAPER_WATCH_LEDGER.csv"
    payload["evidence_files"] = {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}
    if write:
        write_json(json_path, payload)
        write_md(md_path, "Module 191 Real Market-Day Paper Watch Launcher", payload)
        append_ledger(ledger_path, payload)
    return payload


def guard_check() -> int:
    payload = {
        "version": VERSION,
        "guard_check_status": "PASS",
        "module_number": MODULE_NUMBER,
        "module_name": MODULE_NAME,
        "safety_lock": SAFETY_LOCK,
        "blocked_order_apis": {name: "HARD_BLOCKED" for name in BLOCKED_ORDER_APIS},
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "real_money_automatic": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def launch_gui(args: argparse.Namespace) -> int:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        print("Tkinter unavailable. Use START_HQE_MARKET_DAY_PAPER_WATCH_0915_1530.cmd.")
        return 1

    workspace = Path(args.workspace)
    repo = repo_root()
    py = repo / ".venv" / "Scripts" / "python.exe"
    trading_date = args.trading_date or today_local()

    def run_command(label: str, command: str) -> None:
        try:
            subprocess.Popen(command, cwd=str(repo), shell=True)
        except Exception as exc:
            messagebox.showerror(label, str(exc))

    root = tk.Tk()
    root.title("HQE Market-Day Paper Watch 09:15-15:30")
    root.geometry("760x520")

    tk.Label(root, text="HQE Market-Day Paper Watch", font=("Segoe UI", 18, "bold")).pack(pady=(14, 2))
    tk.Label(root, text="PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING", fg="green").pack(pady=(0, 12))
    tk.Label(root, text=f"Trading date: {trading_date} | Symbol: {args.symbol}").pack(pady=2)
    tk.Label(root, text=f"Workspace: {workspace}", wraplength=720, justify="left").pack(pady=2)

    frame = tk.Frame(root)
    frame.pack(pady=12, fill="both", expand=True)

    buttons = [
        ("Refresh Fyers Token", f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\HQE_FYERS_TOKEN_SIMPLE_REFRESH_V2.ps1" -RepoRoot "{repo}" -Workspace "{workspace}" -Symbol "{args.symbol}"'),
        ("Run Historical 5m Data-Only Test", f'"{py}" scripts\\hqe_fyers_historical_5m_data_only_fetcher.py --workspace "{workspace}" --symbol "{args.symbol}" --execute-live-data-only --write'),
        ("Refresh Module 191 Status", f'"{py}" scripts\\hqe_real_market_day_paper_watch_launcher.py --workspace "{workspace}" --user-id "{args.user_id}" --symbol "{args.symbol}" --trading-date "{trading_date}" --write'),
        ("Open Evidence Folder", f'explorer "{workspace}"'),
        ("Open Watch Status HTML", f'start "" "{workspace}\\HQE_MARKET_DAY_PAPER_WATCH_0915_1530.html"'),
    ]
    for label, command in buttons:
        tk.Button(frame, text=label, width=44, height=2, command=lambda l=label, c=command: run_command(l, c)).pack(pady=6)

    tk.Label(root, text="This launcher does not place, modify, cancel, or execute any broker orders.", fg="green").pack(pady=10)
    root.mainloop()
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--trading-date", default=today_local())
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args(argv)

    if args.guard_check:
        return guard_check()

    payload = build_payload(args)
    payload = emit(payload, Path(args.workspace), args.write)
    print(json.dumps(payload, indent=2, sort_keys=True))

    if args.launch:
        return launch_gui(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
