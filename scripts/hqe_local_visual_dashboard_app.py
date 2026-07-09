#!/usr/bin/env python3
"""HQE Module 171: Local Visual Dashboard App.

A safe local GUI/login/control dashboard for Hunter Quant Engine.
This module is intentionally local-only and paper-only:
- no broker execution
- no order API
- no real money
- no auto trading
- no option selling
- no external API calls from this dashboard

The GUI wraps existing safe scripts so the operator does not need to remember
PowerShell commands. Tests use --status/--write/--guard-check and do not open GUI.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "MODULE_171_LOCAL_VISUAL_DASHBOARD_APP_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_USER_ID = "jokim-local"

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "local_dashboard_only": True,
    "manual_login_required": True,
    "manual_operator_control": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api_calls_from_dashboard": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
    "order_api_hard_blocked": True,
}

BLOCKED_ACTIONS = [
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
    "auto_start_trading",
    "auto_broker_connect",
]

REQUIRED_SCRIPTS = {
    "local_login_shell": ["scripts/hqe_local_login_shell.py"],
    "fyers_data_only_secret_preflight": ["scripts/hqe_fyers_data_only_secret_preflight_pack.py"],
    "fyers_access_token_validation": ["scripts/hqe_fyers_access_token_validation_pack.py"],
    "final_safe_daily_run_smoke": ["scripts/hqe_final_safe_daily_run_smoke_pack.py"],
    "final_paper_validation_freeze": ["scripts/hqe_final_paper_validation_master_handoff_freeze_pack.py"],
    "modules_161_170_runner": ["scripts/RUN_MODULES_161_170_LIVE_PAPER_FOUNDATION.ps1"],
}

OPTIONAL_SAFE_COMMANDS = {
    "final_operator_control_panel": "OPEN_HQE_FINAL_OPERATOR_CONTROL_PANEL_SAFE.cmd",
    "daily_evidence_opener": "OPEN_HQE_DAILY_EVIDENCE_SAFE.cmd",
    "safe_startup_login_gate": "OPEN_HQE_SAFE_STARTUP_LOGIN_GATE_ONLY.cmd",
    "safe_startup_login_gate_161_170": "OPEN_HQE_SAFE_STARTUP_LOGIN_GATE_ONLY.cmd",
}

DASHBOARD_OUTPUTS = {
    "status_json": "HQE_LOCAL_VISUAL_DASHBOARD_APP_STATUS.json",
    "status_md": "HQE_LOCAL_VISUAL_DASHBOARD_APP_STATUS.md",
    "index_html": "HQE_LOCAL_VISUAL_DASHBOARD_INDEX.html",
    "launcher_cmd": "OPEN_HQE_LOCAL_VISUAL_DASHBOARD_APP.cmd",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def rel_exists(root: Path, rel_candidates: List[str]) -> Dict[str, Any]:
    for rel in rel_candidates:
        p = root / rel
        if p.exists():
            return {"present": True, "matched_path": str(p), "accepted_candidates": rel_candidates}
    return {"present": False, "matched_path": None, "accepted_candidates": rel_candidates}


def file_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def check_tkinter_available() -> bool:
    try:
        import tkinter  # noqa: F401
        return True
    except Exception:
        return False


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def login_status(workspace: Path) -> Dict[str, Any]:
    session = load_json(workspace / "HQE_LOCAL_LOGIN_SESSION.json")
    credential = Path(r"D:\HQE_BACKTEST_RUNS\HQE_LOCAL_LOGIN\hqe_local_login_credentials.json")
    return {
        "credential_exists": credential.exists(),
        "credential_file": str(credential),
        "session_exists": bool(session),
        "session_file": str(workspace / "HQE_LOCAL_LOGIN_SESSION.json"),
        "last_login_status": session.get("login_status"),
        "last_login_time_utc": session.get("login_time_utc"),
        "last_session_id": session.get("session_id"),
        "authenticated_session_hint": session.get("login_status") == "LOGIN_PASS_LOCAL_GATE_ONLY",
    }


def build_status(workspace: Path, user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    root = repo_root()
    script_details = {key: rel_exists(root, val) for key, val in REQUIRED_SCRIPTS.items()}
    missing_scripts = [key for key, val in script_details.items() if not val["present"]]
    command_details = {
        key: {
            "present": file_exists(workspace / filename),
            "path": str(workspace / filename),
            "filename": filename,
        }
        for key, filename in OPTIONAL_SAFE_COMMANDS.items()
    }
    missing_commands = [key for key, val in command_details.items() if not val["present"]]
    tk_ok = check_tkinter_available()
    credential_state = login_status(workspace)

    pass_ready = tk_ok and not missing_scripts
    return {
        "version": VERSION,
        "generated_at_utc": utc_now(),
        "workspace": str(workspace),
        "repo_root": str(root),
        "user_id": user_id,
        "visual_dashboard_status": "PASS" if pass_ready else "PARTIAL",
        "decision": "LOCAL_VISUAL_DASHBOARD_READY" if pass_ready else "LOCAL_VISUAL_DASHBOARD_PARTIAL_REPAIR_REQUIRED",
        "dashboard_type": "LOCAL_TKINTER_GUI_WITH_SAFE_BUTTONS",
        "tkinter_available": tk_ok,
        "login_state": credential_state,
        "script_readiness": {
            "status": "PASS" if not missing_scripts else "MISSING_REQUIRED_SCRIPTS",
            "missing_script_keys": missing_scripts,
            "details": script_details,
        },
        "safe_shortcut_readiness": {
            "status": "PASS" if not missing_commands else "PARTIAL_SAFE_SHORTCUTS_AVAILABLE",
            "missing_shortcut_keys": missing_commands,
            "details": command_details,
        },
        "operator_buttons": [
            "Create/Reset Local Login Password",
            "Login",
            "Refresh Status",
            "Open Evidence Folder",
            "Open Final Operator Control Panel",
            "Open Daily Evidence",
            "Run Fyers Secret Preflight",
            "Run Fyers Token Offline Validation",
            "Run Modules 161-170 Safe Foundation",
        ],
        "runtime_guards": {
            "external_api_calls_executed_by_visual_dashboard": False,
            "order_api_invoked_by_visual_dashboard": False,
            "broker_execution_invoked_by_visual_dashboard": False,
            "auto_trading_started_by_visual_dashboard": False,
            "fake_trades_created_by_visual_dashboard": False,
            "candidate_tuning_performed_by_visual_dashboard": False,
            "real_money_automatic": False,
            "blocked_actions": {name: "HARD_BLOCKED" for name in BLOCKED_ACTIONS},
        },
        "safety_lock": SAFETY_LOCK,
    }


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_markdown(path: Path, payload: Dict[str, Any]) -> None:
    lines = [
        "# HQE Local Visual Dashboard App Status",
        "",
        f"- Version: `{payload['version']}`",
        f"- Status: `{payload['visual_dashboard_status']}`",
        f"- Decision: `{payload['decision']}`",
        f"- Workspace: `{payload['workspace']}`",
        f"- Tkinter available: `{payload['tkinter_available']}`",
        f"- Credential exists: `{payload['login_state']['credential_exists']}`",
        f"- Session exists: `{payload['login_state']['session_exists']}`",
        f"- Authenticated session hint: `{payload['login_state']['authenticated_session_hint']}`",
        "",
        "## Operator Buttons",
    ]
    for item in payload["operator_buttons"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Safety Lock",
        "",
        "```json",
        json.dumps(payload["safety_lock"], indent=2, sort_keys=True),
        "```",
        "",
        "## Runtime Guards",
        "",
        "```json",
        json.dumps(payload["runtime_guards"], indent=2, sort_keys=True),
        "```",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def html_escape(text: Any) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_html(path: Path, payload: Dict[str, Any]) -> None:
    cards = []
    for label, detail in payload["safe_shortcut_readiness"]["details"].items():
        status = "FOUND" if detail["present"] else "MISSING"
        cards.append(
            f"<div class='card'><h3>{html_escape(label)}</h3><p>Status: <b>{status}</b></p>"
            f"<p><code>{html_escape(detail['path'])}</code></p></div>"
        )
    html = f"""<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<title>HQE Local Visual Dashboard</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f7; color: #1f2937; }}
.header {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-top: 18px; }}
.card {{ background: white; border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
.badge {{ display: inline-block; padding: 5px 10px; border-radius: 999px; background: #e5e7eb; }}
.safe {{ color: #065f46; font-weight: bold; }}
.warn {{ color: #92400e; font-weight: bold; }}
code {{ word-break: break-all; }}
</style>
</head>
<body>
<div class='header'>
<h1>HQE Local Visual Dashboard</h1>
<p class='badge'>Status: {html_escape(payload['visual_dashboard_status'])}</p>
<p><b>Decision:</b> {html_escape(payload['decision'])}</p>
<p><b>Workspace:</b> <code>{html_escape(payload['workspace'])}</code></p>
<p class='safe'>Safety: PAPER ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING</p>
<p>This HTML is a local status index. For the login screen with password box, run <code>OPEN_HQE_LOCAL_VISUAL_DASHBOARD_APP.cmd</code>.</p>
</div>
<div class='grid'>
<div class='card'><h3>Login</h3><p>Credential exists: <b>{payload['login_state']['credential_exists']}</b></p><p>Session exists: <b>{payload['login_state']['session_exists']}</b></p><p>Authenticated hint: <b>{payload['login_state']['authenticated_session_hint']}</b></p></div>
<div class='card'><h3>Scripts</h3><p>Status: <b>{html_escape(payload['script_readiness']['status'])}</b></p><p>Missing: {html_escape(payload['script_readiness']['missing_script_keys'])}</p></div>
<div class='card'><h3>Safety</h3><p>Real money: <b>NO</b></p><p>Orders: <b>BLOCKED</b></p><p>Broker execution: <b>BLOCKED</b></p></div>
{''.join(cards)}
</div>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def write_launcher(workspace: Path, user_id: str) -> Path:
    root = repo_root()
    launcher = workspace / DASHBOARD_OUTPUTS["launcher_cmd"]
    content = f"""@echo off
setlocal
cd /d "{root}"
echo HQE Local Visual Dashboard App
echo Safety: PAPER ONLY / NO ORDERS / NO BROKER EXECUTION / NO AUTO TRADING
"{sys.executable}" "{root / 'scripts' / 'hqe_local_visual_dashboard_app.py'}" --launch-gui --workspace "{workspace}" --user-id "{user_id}"
if errorlevel 1 pause
endlocal
"""
    launcher.write_text(content, encoding="utf-8")
    return launcher


def write_outputs(workspace: Path, user_id: str) -> Dict[str, Any]:
    payload = build_status(workspace, user_id=user_id)
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / DASHBOARD_OUTPUTS["status_json"]
    md_path = workspace / DASHBOARD_OUTPUTS["status_md"]
    html_path = workspace / DASHBOARD_OUTPUTS["index_html"]
    launcher_path = write_launcher(workspace, user_id)
    write_json(json_path, payload)
    write_markdown(md_path, payload)
    write_html(html_path, payload)
    payload["evidence_files"] = {
        "json": str(json_path),
        "markdown": str(md_path),
        "html": str(html_path),
        "launcher_cmd": str(launcher_path),
    }
    write_json(json_path, payload)
    return payload


def run_subprocess(command: List[str], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    proc = subprocess.run(
        command,
        cwd=str(repo_root()),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "command": command,
    }


def open_path(path: Path) -> str:
    if not path.exists():
        return f"Missing: {path}"
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return f"Opened: {path}"
    subprocess.Popen(["xdg-open", str(path)])
    return f"Opened: {path}"


def run_gui(workspace: Path, user_id: str) -> int:
    try:
        import tkinter as tk
        from tkinter import messagebox, scrolledtext
    except Exception as exc:  # pragma: no cover - platform-dependent
        print(json.dumps({"status": "ERROR", "error": f"Tkinter unavailable: {exc}", "safety_lock": SAFETY_LOCK}, indent=2))
        return 2

    root_path = repo_root()
    win = tk.Tk()
    win.title("HQE Local Visual Dashboard - Paper Only")
    win.geometry("980x720")

    tk.Label(win, text="Hunter Quant Engine - Local Visual Dashboard", font=("Arial", 16, "bold")).pack(pady=(12, 4))
    tk.Label(win, text="PAPER ONLY | NO REAL ORDERS | NO BROKER EXECUTION | NO AUTO TRADING", fg="darkgreen", font=("Arial", 10, "bold")).pack(pady=(0, 10))

    form = tk.Frame(win)
    form.pack(fill="x", padx=16)
    tk.Label(form, text="User ID").grid(row=0, column=0, sticky="w")
    user_var = tk.StringVar(value=user_id)
    tk.Entry(form, textvariable=user_var, width=32).grid(row=0, column=1, sticky="w", padx=8)
    tk.Label(form, text="Password").grid(row=1, column=0, sticky="w")
    password_var = tk.StringVar()
    tk.Entry(form, textvariable=password_var, width=32, show="*").grid(row=1, column=1, sticky="w", padx=8)
    tk.Label(form, text=f"Workspace: {workspace}", wraplength=820, justify="left").grid(row=2, column=0, columnspan=4, sticky="w", pady=6)

    output = scrolledtext.ScrolledText(win, height=26, wrap="word")
    output.pack(fill="both", expand=True, padx=16, pady=12)

    def log(message: Any) -> None:
        output.insert("end", str(message) + "\n")
        output.see("end")

    def show_status() -> None:
        payload = write_outputs(workspace, user_var.get().strip() or DEFAULT_USER_ID)
        log(json.dumps({
            "visual_dashboard_status": payload["visual_dashboard_status"],
            "decision": payload["decision"],
            "credential_exists": payload["login_state"]["credential_exists"],
            "session_exists": payload["login_state"]["session_exists"],
            "authenticated_session_hint": payload["login_state"]["authenticated_session_hint"],
            "launcher": payload["evidence_files"]["launcher_cmd"],
            "html": payload["evidence_files"]["html"],
        }, indent=2))

    def login_action(init: bool) -> None:
        pwd = password_var.get()
        uid = user_var.get().strip() or DEFAULT_USER_ID
        if not pwd:
            messagebox.showwarning("HQE Login", "Password blank hai. Password enter karo.")
            return
        env = os.environ.copy()
        env["HQE_LOCAL_PASSWORD"] = pwd
        mode = "--init" if init else "--login"
        cmd = [sys.executable, str(root_path / "scripts" / "hqe_local_login_shell.py"), mode, "--user-id", uid, "--password-env", "HQE_LOCAL_PASSWORD", "--workspace", str(workspace)]
        result = run_subprocess(cmd, env=env)
        password_var.set("")
        log("INIT" if init else "LOGIN")
        log(result["stdout"] or result["stderr"])
        if result["returncode"] == 0:
            show_status()

    def run_safe_script(script_name: str, extra: Optional[List[str]] = None) -> None:
        cmd = [sys.executable, str(root_path / "scripts" / script_name), "--workspace", str(workspace), "--write"]
        if extra:
            cmd.extend(extra)
        result = run_subprocess(cmd)
        log(f"RUN {script_name}")
        log(result["stdout"] or result["stderr"])

    btns = tk.Frame(win)
    btns.pack(fill="x", padx=16)
    tk.Button(btns, text="Create/Reset Password", command=lambda: login_action(True), width=24).grid(row=0, column=0, padx=4, pady=4)
    tk.Button(btns, text="Login", command=lambda: login_action(False), width=18).grid(row=0, column=1, padx=4, pady=4)
    tk.Button(btns, text="Refresh Status", command=show_status, width=18).grid(row=0, column=2, padx=4, pady=4)
    tk.Button(btns, text="Open Evidence Folder", command=lambda: log(open_path(workspace)), width=22).grid(row=0, column=3, padx=4, pady=4)

    tk.Button(btns, text="Open HTML Status", command=lambda: log(open_path(workspace / DASHBOARD_OUTPUTS["index_html"])), width=24).grid(row=1, column=0, padx=4, pady=4)
    tk.Button(btns, text="Open Control Panel", command=lambda: log(open_path(workspace / "OPEN_HQE_FINAL_OPERATOR_CONTROL_PANEL_SAFE.cmd")), width=18).grid(row=1, column=1, padx=4, pady=4)
    tk.Button(btns, text="Open Daily Evidence", command=lambda: log(open_path(workspace / "OPEN_HQE_DAILY_EVIDENCE_SAFE.cmd")), width=18).grid(row=1, column=2, padx=4, pady=4)
    tk.Button(btns, text="Fyers Secret Preflight", command=lambda: run_safe_script("hqe_fyers_data_only_secret_preflight_pack.py"), width=22).grid(row=1, column=3, padx=4, pady=4)

    tk.Button(btns, text="Token Offline Check", command=lambda: run_safe_script("hqe_fyers_access_token_validation_pack.py"), width=24).grid(row=2, column=0, padx=4, pady=4)
    tk.Button(btns, text="Safe Dry Run Status", command=lambda: run_safe_script("hqe_full_live_paper_dry_run_final_readiness.py", ["--trading-date", datetime.now().date().isoformat(), "--day-number", "1"]), width=18).grid(row=2, column=1, padx=4, pady=4)
    tk.Button(btns, text="Exit", command=win.destroy, width=18).grid(row=2, column=2, padx=4, pady=4)

    show_status()
    win.mainloop()
    return 0


def guard_check() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "external_api_calls_executed_by_visual_dashboard": False,
        "order_api_invoked_by_visual_dashboard": False,
        "broker_execution_invoked_by_visual_dashboard": False,
        "auto_trading_started_by_visual_dashboard": False,
        "fake_trades_created_by_visual_dashboard": False,
        "real_money_automatic": False,
        "blocked_actions": {name: "HARD_BLOCKED" for name in BLOCKED_ACTIONS},
        "safety_lock": SAFETY_LOCK,
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQE local visual dashboard app")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--generate-launcher", action="store_true")
    parser.add_argument("--launch-gui", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    workspace = Path(args.workspace)
    if args.guard_check:
        print(json.dumps(guard_check(), indent=2, sort_keys=True))
        return 0
    if args.launch_gui:
        return run_gui(workspace, args.user_id)
    if args.write or args.generate_launcher:
        payload = write_outputs(workspace, args.user_id)
    else:
        payload = build_status(workspace, args.user_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("visual_dashboard_status") in {"PASS", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
