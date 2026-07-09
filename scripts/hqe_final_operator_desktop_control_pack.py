#!/usr/bin/env python3
"""HQE Module 157: Final Operator Desktop Control Pack.

This module emits a safe local operator control panel for the HQE daily workflow.
It does not connect to brokers, does not call external APIs, does not start auto
trading, and does not create trades. It only writes local evidence files and a
manual operator command launcher.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

VERSION = "MODULE_157_FINAL_OPERATOR_DESKTOP_CONTROL_PACK_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_TRADING_DATE = "2026-07-09"
DEFAULT_DAY_NUMBER = 1

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "local_files_only": True,
    "manual_operator_control_required": True,
    "manual_login_required": True,
    "data_only": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api_from_control_pack": True,
    "no_plaintext_secret_storage": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}

REQUIRED_OPERATOR_SCRIPTS: List[Tuple[str, str]] = [
    ("local_login_shell", r"scripts\hqe_local_login_shell.py"),
    ("fyers_data_only_preflight", r"scripts\hqe_fyers_data_only_connector.py"),
    ("market_session_supervisor", r"scripts\hqe_market_session_supervisor.py"),
    ("paper_signal_no_trade_reason_engine", r"scripts\hqe_paper_signal_no_trade_reason_engine.py"),
    ("day_close_recorder", r"scripts\hqe_forward_validation_day_close_recorder.py"),
    ("day_ledger_evaluator", r"scripts\evaluate_forward_validation_day_ledger.py"),
    ("valid_trade_day_tracker", r"scripts\hqe_30_valid_trade_day_tracker.py"),
    ("final_daily_app_flow_integration", r"scripts\hqe_final_daily_app_flow_integration_pack.py"),
    ("final_daily_run_decision_pack", r"scripts\hqe_final_daily_run_decision_pack.py"),
    ("manual_daily_launch_command_pack", r"scripts\hqe_manual_daily_launch_command_pack.py"),
    ("final_daily_evidence_auto_open_pack", r"scripts\hqe_final_daily_evidence_auto_open_pack.py"),
]

FORBIDDEN_COMMAND_TOKENS = [
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def as_repo_relative(path_text: str) -> Path:
    return Path(path_text.replace("\\", os.sep))


def inventory_required_scripts(repo_root: Path) -> List[Dict[str, Any]]:
    inventory: List[Dict[str, Any]] = []
    for key, relative_text in REQUIRED_OPERATOR_SCRIPTS:
        relative_path = as_repo_relative(relative_text)
        absolute_path = repo_root / relative_path
        inventory.append(
            {
                "key": key,
                "relative_path": str(relative_path).replace(os.sep, "\\"),
                "exists": absolute_path.exists(),
            }
        )
    return inventory


def missing_required_scripts(repo_root: Path) -> List[str]:
    return [item["relative_path"] for item in inventory_required_scripts(repo_root) if not item["exists"]]


def ps_quote(text: str) -> str:
    return '"' + text.replace('"', '`"') + '"'


def build_safe_operator_commands(workspace: Path, trading_date: str, day_number: int) -> List[Dict[str, str]]:
    workspace_text = str(workspace)
    day_text = str(int(day_number))
    commands = [
        {
            "step": "01_login_status_gate",
            "purpose": "Check local HQE login-shell status; does not authenticate automatically.",
            "command": r'.\.venv\Scripts\python.exe scripts\hqe_local_login_shell.py --status',
        },
        {
            "step": "02_final_daily_run_decision_pack",
            "purpose": "Build launch readiness evidence before any manual daily run.",
            "command": f'.\\.venv\\Scripts\\python.exe scripts\\hqe_final_daily_run_decision_pack.py --workspace {ps_quote(workspace_text)} --trading-date {ps_quote(trading_date)} --day-number {day_text} --write',
        },
        {
            "step": "03_market_session_supervisor_status",
            "purpose": "Check whether current local market-session state is pre-market, active window, or post-market.",
            "command": f'.\\.venv\\Scripts\\python.exe scripts\\hqe_market_session_supervisor.py --workspace {ps_quote(workspace_text)} --write',
        },
        {
            "step": "04_fyers_data_only_preflight",
            "purpose": "Check future data-only Fyers readiness without starting live transport or order APIs.",
            "command": f'.\\.venv\\Scripts\\python.exe scripts\\hqe_fyers_data_only_connector.py --preflight --workspace {ps_quote(workspace_text)} --write',
        },
        {
            "step": "05_paper_signal_no_trade_reason",
            "purpose": "Record paper signal/no-trade reason using existing local evidence only.",
            "command": f'.\\.venv\\Scripts\\python.exe scripts\\hqe_paper_signal_no_trade_reason_engine.py --workspace {ps_quote(workspace_text)} --trading-date {ps_quote(trading_date)} --day-number {day_text} --write',
        },
        {
            "step": "06_day_ledger_evaluator",
            "purpose": "Evaluate observed sessions, valid trade days, actual paper trades, and expiry weeks.",
            "command": f'.\\.venv\\Scripts\\python.exe scripts\\evaluate_forward_validation_day_ledger.py --workspace {ps_quote(workspace_text)} --write',
        },
        {
            "step": "07_30_valid_trade_day_tracker",
            "purpose": "Track 30 valid paper trade-day target; no-trade days do not count toward target.",
            "command": f'.\\.venv\\Scripts\\python.exe scripts\\hqe_30_valid_trade_day_tracker.py --workspace {ps_quote(workspace_text)} --write',
        },
        {
            "step": "08_final_daily_app_flow_integration",
            "purpose": "Build final integrated daily flow evidence pack.",
            "command": f'.\\.venv\\Scripts\\python.exe scripts\\hqe_final_daily_app_flow_integration_pack.py --workspace {ps_quote(workspace_text)} --trading-date {ps_quote(trading_date)} --day-number {day_text} --write',
        },
        {
            "step": "09_evidence_shortcut_pack",
            "purpose": "Create local evidence/report open shortcut; does not open automatically in this pack.",
            "command": f'.\\.venv\\Scripts\\python.exe scripts\\hqe_final_daily_evidence_auto_open_pack.py --workspace {ps_quote(workspace_text)} --trading-date {ps_quote(trading_date)} --day-number {day_text} --write',
        },
    ]
    return commands


def command_contains_forbidden_token(command: str) -> bool:
    lowered = command.lower()
    return any(token.lower() in lowered for token in FORBIDDEN_COMMAND_TOKENS)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def build_markdown(payload: Dict[str, Any]) -> str:
    commands = payload["operator_commands"]
    inventory = payload["script_inventory"]
    lines: List[str] = []
    lines.append("# HQE Final Operator Desktop Control Pack")
    lines.append("")
    lines.append(f"- Version: `{payload['version']}`")
    lines.append(f"- Status: `{payload['control_pack_status']}`")
    lines.append(f"- Decision: `{payload['decision']}`")
    lines.append(f"- Workspace: `{payload['workspace']}`")
    lines.append(f"- Trading date: `{payload['trading_date']}`")
    lines.append(f"- Day number: `{payload['day_number']}`")
    lines.append("")
    lines.append("## Safety Lock")
    lines.append("")
    for key, value in payload["safety_lock"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Required Script Inventory")
    lines.append("")
    for item in inventory:
        lines.append(f"- {item['key']}: `{item['relative_path']}` exists=`{item['exists']}`")
    lines.append("")
    lines.append("## Manual Operator Commands")
    lines.append("")
    lines.append("Run these manually only after login/operator review. They do not place orders.")
    lines.append("")
    for command in commands:
        lines.append(f"### {command['step']}")
        lines.append("")
        lines.append(command["purpose"])
        lines.append("")
        lines.append("```powershell")
        lines.append(command["command"])
        lines.append("```")
        lines.append("")
    lines.append("## Guard Results")
    lines.append("")
    lines.append(f"- external_api_calls_executed_by_control_pack: `{payload['external_api_calls_executed_by_control_pack']}`")
    lines.append(f"- order_api_invoked_by_control_pack: `{payload['order_api_invoked_by_control_pack']}`")
    lines.append(f"- broker_execution_invoked_by_control_pack: `{payload['broker_execution_invoked_by_control_pack']}`")
    lines.append(f"- auto_trading_started_by_control_pack: `{payload['auto_trading_started_by_control_pack']}`")
    lines.append(f"- fake_trades_created_by_control_pack: `{payload['fake_trades_created_by_control_pack']}`")
    lines.append(f"- real_money_automatic: `{payload['real_money_automatic']}`")
    return "\n".join(lines) + "\n"


def build_operator_cmd(payload: Dict[str, Any]) -> str:
    workspace = payload["workspace"]
    date = payload["trading_date"]
    day = payload["day_number"]
    lines = [
        "@echo off",
        "setlocal",
        "title HQE Final Operator Desktop Control Pack",
        "cd /d D:\\Hunter_Quant_Engine_PC_TRANSFER",
        "echo HQE FINAL OPERATOR DESKTOP CONTROL PACK",
        "echo ------------------------------------------------------------",
        "echo Safety: PAPER ONLY / NO ORDERS / NO BROKER EXECUTION / NO AUTO TRADING",
        "echo Workspace: " + workspace,
        "echo Trading Date: " + date,
        "echo Day Number: " + str(day),
        "echo ------------------------------------------------------------",
        "echo.",
        "echo 1. Login status gate",
        r'.\.venv\Scripts\python.exe scripts\hqe_local_login_shell.py --status',
        "echo.",
        "echo 2. Final daily run decision pack",
        f'.\\.venv\\Scripts\\python.exe scripts\\hqe_final_daily_run_decision_pack.py --workspace "{workspace}" --trading-date "{date}" --day-number {day} --write',
        "echo.",
        "echo 3. Evidence shortcut pack",
        f'.\\.venv\\Scripts\\python.exe scripts\\hqe_final_daily_evidence_auto_open_pack.py --workspace "{workspace}" --trading-date "{date}" --day-number {day} --write',
        "echo.",
        "echo Done. Review evidence files manually.",
        "pause",
        "endlocal",
        "",
    ]
    return "\r\n".join(lines)


def build_control_pack(repo_root: Path, workspace: Path, trading_date: str, day_number: int) -> Dict[str, Any]:
    inventory = inventory_required_scripts(repo_root)
    missing = [item["relative_path"] for item in inventory if not item["exists"]]
    operator_commands = build_safe_operator_commands(workspace, trading_date, day_number)
    command_guard_violations = [
        command["step"] for command in operator_commands if command_contains_forbidden_token(command["command"])
    ]

    status = "PASS" if not command_guard_violations else "FAIL"
    decision = (
        "FINAL_OPERATOR_DESKTOP_CONTROL_PACK_READY_MANUAL_REVIEW_REQUIRED"
        if not missing and status == "PASS"
        else "FINAL_OPERATOR_DESKTOP_CONTROL_PACK_READY_WITH_MISSING_LOCAL_SCRIPTS"
    )
    if command_guard_violations:
        decision = "CONTROL_PACK_BLOCKED_FOR_FORBIDDEN_COMMAND_TOKEN"

    payload: Dict[str, Any] = {
        "version": VERSION,
        "generated_at_utc": utc_now_iso(),
        "repo_root": str(repo_root),
        "workspace": str(workspace),
        "trading_date": trading_date,
        "day_number": int(day_number),
        "control_pack_status": status,
        "decision": decision,
        "operator_mode": "FINAL_DESKTOP_CONTROL_PANEL_LOCAL_ONLY",
        "manual_login_required": True,
        "manual_operator_review_required": True,
        "control_panel_emitted": True,
        "desktop_shortcut_installed_by_this_run": False,
        "scheduled_task_installed_by_this_run": False,
        "script_inventory": inventory,
        "missing_required_scripts": missing,
        "operator_commands": operator_commands,
        "forbidden_command_guard_violations": command_guard_violations,
        "external_api_calls_executed_by_control_pack": False,
        "order_api_invoked_by_control_pack": False,
        "broker_execution_invoked_by_control_pack": False,
        "auto_trading_started_by_control_pack": False,
        "real_order_created_by_control_pack": False,
        "fake_trades_created_by_control_pack": False,
        "candidate_tuning_performed_by_control_pack": False,
        "real_money_automatic": False,
        "profitability_claim_made": False,
        "safety_lock": dict(SAFETY_LOCK),
    }
    return payload


def write_control_pack_outputs(payload: Dict[str, Any], workspace: Path) -> Dict[str, str]:
    json_path = workspace / "HQE_FINAL_OPERATOR_DESKTOP_CONTROL_PACK.json"
    md_path = workspace / "HQE_FINAL_OPERATOR_DESKTOP_CONTROL_PACK.md"
    csv_path = workspace / "HQE_FINAL_OPERATOR_DESKTOP_CONTROL_COMMANDS.csv"
    cmd_path = workspace / "OPEN_HQE_FINAL_OPERATOR_CONTROL_PANEL_SAFE.cmd"

    write_json(json_path, payload)
    write_text(md_path, build_markdown(payload))
    write_csv(
        csv_path,
        payload["operator_commands"],
        ["step", "purpose", "command"],
    )
    write_text(cmd_path, build_operator_cmd(payload))
    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "commands_csv": str(csv_path),
        "safe_cmd_launcher": str(cmd_path),
    }


def guard_check() -> Dict[str, Any]:
    sample_commands = build_safe_operator_commands(DEFAULT_WORKSPACE, DEFAULT_TRADING_DATE, DEFAULT_DAY_NUMBER)
    violations = [command["step"] for command in sample_commands if command_contains_forbidden_token(command["command"])]
    return {
        "version": VERSION,
        "guard_check_status": "PASS" if not violations else "FAIL",
        "forbidden_command_guard_violations": violations,
        "external_api_calls_executed_by_guard_check": False,
        "order_api_invoked_by_guard_check": False,
        "broker_execution_invoked_by_guard_check": False,
        "auto_trading_started_by_guard_check": False,
        "fake_trades_created_by_guard_check": False,
        "real_money_automatic": False,
        "safety_lock": dict(SAFETY_LOCK),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQE Module 157 final operator desktop control pack")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="HQE forward validation workspace")
    parser.add_argument("--trading-date", default=DEFAULT_TRADING_DATE, help="Trading date YYYY-MM-DD")
    parser.add_argument("--day-number", default=DEFAULT_DAY_NUMBER, type=int, help="Forward validation day number")
    parser.add_argument("--repo-root", default=".", help="Repository root; default current directory")
    parser.add_argument("--write", action="store_true", help="Write local evidence files into workspace")
    parser.add_argument("--guard-check", action="store_true", help="Run safety guard check only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.guard_check:
        print(json.dumps(guard_check(), indent=2, sort_keys=True))
        return 0

    repo_root = Path(args.repo_root).resolve()
    workspace = Path(args.workspace)
    payload = build_control_pack(repo_root, workspace, args.trading_date, args.day_number)
    if args.write:
        payload["evidence_files"] = write_control_pack_outputs(payload, workspace)
        # Re-write JSON after adding evidence paths.
        write_json(workspace / "HQE_FINAL_OPERATOR_DESKTOP_CONTROL_PACK.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["control_pack_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
