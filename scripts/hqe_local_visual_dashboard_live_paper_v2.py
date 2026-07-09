from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from hqe_live_paper_ops_172_180_common import add_common_cli, as_path, base_payload, create_cmd, guard_payload, print_payload, repo_python, write_outputs

MODULE_NUMBER = 176
MODULE_NAME = "HQE Local Visual Dashboard Live Paper V2"
BASENAME = "MODULE_176_LOCAL_VISUAL_DASHBOARD_LIVE_PAPER_V2_STATUS"


def _repo_root() -> Path:
    return Path.cwd()


def _py() -> str:
    return str(_repo_root() / ".venv" / "Scripts" / "python.exe")


def run_cmd(args: List[str]) -> str:
    cp = subprocess.run(args, cwd=str(_repo_root()), text=True, capture_output=True)
    return (cp.stdout or "") + ("\nSTDERR:\n" + cp.stderr if cp.stderr else "")


def launch_gui(workspace: Path, user_id: str, symbol: str) -> None:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext

    root = tk.Tk()
    root.title("HQE Visual Dashboard V2 - Paper Only")
    root.geometry("920x640")

    tk.Label(root, text="Hunter Quant Engine - Live Paper Dashboard V2", font=("Arial", 15, "bold")).pack(pady=8)
    tk.Label(root, text="PAPER ONLY | DATA ONLY | NO ORDERS | NO BROKER EXECUTION | NO AUTO TRADING", fg="green", font=("Arial", 10, "bold")).pack()

    frame = tk.Frame(root)
    frame.pack(fill="x", padx=10, pady=8)
    tk.Label(frame, text="User ID").grid(row=0, column=0, sticky="w")
    user_entry = tk.Entry(frame, width=24)
    user_entry.insert(0, user_id)
    user_entry.grid(row=0, column=1, padx=5)
    tk.Label(frame, text="Password").grid(row=1, column=0, sticky="w")
    pass_entry = tk.Entry(frame, width=24, show="*")
    pass_entry.grid(row=1, column=1, padx=5)
    tk.Label(frame, text=f"Workspace: {workspace}").grid(row=2, column=0, columnspan=4, sticky="w", pady=4)
    tk.Label(frame, text=f"Symbol: {symbol}").grid(row=3, column=0, columnspan=4, sticky="w")

    output = scrolledtext.ScrolledText(root, height=24, width=110)
    output.pack(fill="both", expand=True, padx=10, pady=5)

    def show(text: str) -> None:
        output.delete("1.0", tk.END)
        output.insert(tk.END, text)

    def login() -> None:
        pwd = pass_entry.get()
        if not pwd:
            messagebox.showwarning("HQE", "Password required")
            return
        env = os.environ.copy()
        env["HQE_LOCAL_PASSWORD"] = pwd
        cp = subprocess.run([
            _py(), "scripts/hqe_local_login_shell.py", "--login", "--user-id", user_entry.get(), "--password-env", "HQE_LOCAL_PASSWORD", "--workspace", str(workspace)
        ], cwd=str(_repo_root()), text=True, capture_output=True, env=env)
        show((cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else ""))

    def run_script(script: str, *extra: str) -> None:
        show(run_cmd([_py(), f"scripts/{script}", "--workspace", str(workspace), "--user-id", user_entry.get(), "--symbol", symbol, "--write", *extra]))

    buttons = tk.Frame(root)
    buttons.pack(fill="x", padx=10, pady=5)
    actions = [
        ("Login", login),
        ("Refresh Login Status", lambda: show(run_cmd([_py(), "scripts/hqe_local_login_shell.py", "--status", "--workspace", str(workspace)]))),
        ("Test Fyers LTP Data-Only", lambda: run_script("hqe_fyers_live_data_only_ltp_test.py", "--execute-live-data-only")),
        ("Fetch 5m Candles Data-Only", lambda: run_script("hqe_fyers_historical_5m_data_only_fetcher.py", "--execute-live-data-only")),
        ("Symbol Config Guard", lambda: run_script("hqe_live_data_symbol_config_guard.py")),
        ("Generate Next Day", lambda: run_script("hqe_day2_next_paper_session_generator.py")),
        ("Session Launch Plan", lambda: run_script("hqe_one_click_live_paper_session_launcher_plan.py")),
        ("Report Index V2", lambda: run_script("hqe_live_paper_report_index_v2.py")),
        ("Final Readiness", lambda: run_script("hqe_live_paper_operations_final_readiness_pack.py")),
        ("Open Evidence Folder", lambda: os.startfile(str(workspace))),
    ]
    for idx, (label, fn) in enumerate(actions):
        tk.Button(buttons, text=label, width=24, command=fn).grid(row=idx // 2, column=idx % 2, padx=4, pady=3, sticky="ew")
    root.mainloop()


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = as_path(args.workspace)
    launcher = workspace / "OPEN_HQE_VISUAL_DASHBOARD_V2_LIVE_PAPER.cmd"
    html = workspace / "HQE_VISUAL_DASHBOARD_V2_STATUS.html"
    payload = base_payload(MODULE_NUMBER, MODULE_NAME, workspace, args.trading_date, args.day_number)
    payload.update({
        "visual_dashboard_v2_status": "PASS",
        "decision": "VISUAL_DASHBOARD_V2_READY_WITH_LIVE_DATA_ONLY_BUTTONS",
        "user_id": args.user_id,
        "symbol": args.symbol,
        "dashboard_buttons": [
            "Login", "Refresh Login Status", "Test Fyers LTP Data-Only", "Fetch 5m Candles Data-Only",
            "Symbol Config Guard", "Generate Next Day", "Session Launch Plan", "Report Index V2", "Final Readiness", "Open Evidence Folder",
        ],
        "launcher_path": str(launcher),
        "html_status_path": str(html),
        "external_api_calls_executed_by_module_176": False,
        "order_api_invoked_by_module_176": False,
        "broker_execution_invoked_by_module_176": False,
        "auto_trading_started_by_module_176": False,
        "fake_trades_created_by_module_176": False,
    })
    if args.write:
        create_cmd(launcher, [
            f'cd /d "{Path.cwd()}"',
            f'"{_py()}" scripts\\hqe_local_visual_dashboard_live_paper_v2.py --workspace "{workspace}" --user-id "{args.user_id}" --symbol "{args.symbol}"',
        ])
        html.write_text("""<!doctype html><html><body><h1>HQE Visual Dashboard V2</h1><p>Paper-only live data dashboard launcher ready.</p><p>No orders. No broker execution. No auto trading.</p></body></html>""", encoding="utf-8")
        payload["evidence_files"] = write_outputs(payload, workspace, BASENAME)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    add_common_cli(parser)
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()
    if args.guard_check:
        print_payload(guard_payload(MODULE_NUMBER, MODULE_NAME))
        return 0
    if args.launch:
        launch_gui(as_path(args.workspace), args.user_id, args.symbol)
        return 0
    payload = build_payload(args)
    print_payload(payload)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
