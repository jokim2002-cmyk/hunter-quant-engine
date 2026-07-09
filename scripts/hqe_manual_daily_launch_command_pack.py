#!/usr/bin/env python3
"""HQE Module 155: Manual Daily Launch Command Pack / One-Click Safe Run.

This module creates a local-only operator launch plan for the daily HQE paper
validation flow. It does not place orders, does not start broker execution, and
never creates fake trades. It only prepares/validates a safe command sequence and
optionally writes local evidence files plus a manual PowerShell launcher.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

VERSION = "MODULE_155_MANUAL_DAILY_LAUNCH_COMMAND_PACK_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_TRADING_DATE = "2026-07-09"
DEFAULT_DAY_NUMBER = 1

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "data_only": True,
    "local_only_launch_pack": True,
    "manual_login_required": True,
    "no_auto_trading": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_real_money": True,
    "no_option_selling": True,
    "no_external_api_calls_from_launch_pack": True,
    "no_plaintext_secret_storage": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}

REQUIRED_SCRIPTS: List[Tuple[str, str]] = [
    ("local_login_status_gate", "scripts/hqe_local_login_shell.py"),
    ("fyers_data_only_preflight", "scripts/hqe_fyers_data_only_connector.py"),
    ("market_session_supervisor", "scripts/hqe_market_session_supervisor.py"),
    ("paper_signal_no_trade_reason", "scripts/hqe_paper_signal_no_trade_reason_engine.py"),
    ("thirty_valid_trade_day_tracker", "scripts/hqe_30_valid_trade_day_tracker.py"),
    ("pc_startup_auto_open_scheduler", "scripts/hqe_pc_startup_auto_open_scheduler.py"),
    ("final_daily_app_flow_integration", "scripts/hqe_final_daily_app_flow_integration_pack.py"),
    ("final_daily_run_decision_pack", "scripts/hqe_final_daily_run_decision_pack.py"),
]

BLOCKED_COMMAND_TOKENS = [
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


def ps_quote(value: str) -> str:
    return '"' + value.replace('"', '`"') + '"'


def repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root)).replace("/", "\\")
    except ValueError:
        return str(path).replace("/", "\\")


def _python_expr(repo_root: Path) -> str:
    return r".\.venv\Scripts\python.exe"


def check_required_scripts(repo_root: Path) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    missing: List[str] = []
    for name, rel_path in REQUIRED_SCRIPTS:
        path = repo_root / rel_path
        exists = path.exists()
        if not exists:
            missing.append(rel_path)
        checks.append({
            "name": name,
            "relative_path": rel_path.replace("/", "\\"),
            "exists": exists,
        })
    return {
        "checks": checks,
        "missing_required_scripts": missing,
        "all_required_scripts_present": not missing,
    }


def build_safe_commands(repo_root: Path, workspace: Path, trading_date: str, day_number: int) -> List[Dict[str, Any]]:
    py = _python_expr(repo_root)
    workspace_s = str(workspace)
    commands = [
        {
            "step": 1,
            "name": "login_status_gate",
            "purpose": "Check local login/session status only. Manual login remains required.",
            "command": f"& {py} scripts\\hqe_local_login_shell.py --status",
            "executes_external_api": False,
            "executes_order_api": False,
            "starts_auto_trading": False,
        },
        {
            "step": 2,
            "name": "launch_readiness_decision_pack",
            "purpose": "Validate final launch readiness and safety locks before operator run.",
            "command": f"& {py} scripts\\hqe_final_daily_run_decision_pack.py --workspace {ps_quote(workspace_s)} --trading-date {ps_quote(trading_date)} --day-number {day_number} --write",
            "executes_external_api": False,
            "executes_order_api": False,
            "starts_auto_trading": False,
        },
        {
            "step": 3,
            "name": "market_session_supervisor",
            "purpose": "Classify pre-market/in-session/post-market state for the local paper workflow.",
            "command": f"& {py} scripts\\hqe_market_session_supervisor.py --workspace {ps_quote(workspace_s)} --write",
            "executes_external_api": False,
            "executes_order_api": False,
            "starts_auto_trading": False,
        },
        {
            "step": 4,
            "name": "fyers_data_only_preflight",
            "purpose": "Check data-only connector readiness. This shell must not start transport or execute external API calls.",
            "command": f"& {py} scripts\\hqe_fyers_data_only_connector.py --preflight --workspace {ps_quote(workspace_s)} --write",
            "executes_external_api": False,
            "executes_order_api": False,
            "starts_auto_trading": False,
        },
        {
            "step": 5,
            "name": "paper_signal_no_trade_reason_engine",
            "purpose": "Record paper signal/no-trade reason from real local feed evidence only; no fake trades.",
            "command": f"& {py} scripts\\hqe_paper_signal_no_trade_reason_engine.py --workspace {ps_quote(workspace_s)} --trading-date {ps_quote(trading_date)} --day-number {day_number} --write",
            "executes_external_api": False,
            "executes_order_api": False,
            "starts_auto_trading": False,
        },
        {
            "step": 6,
            "name": "thirty_valid_trade_day_tracker",
            "purpose": "Update observed session day vs 30 valid trade-day validation counters.",
            "command": f"& {py} scripts\\hqe_30_valid_trade_day_tracker.py --workspace {ps_quote(workspace_s)} --write",
            "executes_external_api": False,
            "executes_order_api": False,
            "starts_auto_trading": False,
        },
        {
            "step": 7,
            "name": "final_daily_app_flow_integration_pack",
            "purpose": "Write final daily app flow integration evidence for manual review.",
            "command": f"& {py} scripts\\hqe_final_daily_app_flow_integration_pack.py --workspace {ps_quote(workspace_s)} --trading-date {ps_quote(trading_date)} --day-number {day_number} --write",
            "executes_external_api": False,
            "executes_order_api": False,
            "starts_auto_trading": False,
        },
    ]
    return commands


def detect_blocked_tokens(commands: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
    hits: List[Dict[str, str]] = []
    for command in commands:
        text = str(command.get("command", "")).lower()
        for token in BLOCKED_COMMAND_TOKENS:
            if token.lower() in text:
                hits.append({"step": str(command.get("step", "")), "token": token})
    return hits


def build_launcher_text(commands: List[Dict[str, Any]], workspace: Path, trading_date: str, day_number: int) -> str:
    lines = [
        "$ErrorActionPreference = 'Stop'",
        "Set-Location \"D:\\Hunter_Quant_Engine_PC_TRANSFER\"",
        "Write-Host 'HQE DAILY SAFE LAUNCH - PAPER ONLY / DATA ONLY / MANUAL LOGIN REQUIRED'",
        "Write-Host 'No real money, no orders, no broker execution, no auto trading.'",
        f"Write-Host 'Workspace: {str(workspace)}'",
        f"Write-Host 'Trading date: {trading_date} | Day number: {day_number}'",
        "",
    ]
    for command in commands:
        lines.append(f"Write-Host 'STEP {command['step']}: {command['name']}'")
        lines.append(command["command"])
        lines.append("")
    lines.append("Write-Host 'HQE DAILY SAFE LAUNCH PACK COMPLETE - REVIEW EVIDENCE FILES BEFORE NEXT ACTION.'")
    lines.append("")
    return "\n".join(lines)


def build_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# HQE Manual Daily Launch Command Pack",
        "",
        f"- Version: `{payload['version']}`",
        f"- Status: `{payload['launch_pack_status']}`",
        f"- Decision: `{payload['decision']}`",
        f"- Workspace: `{payload['workspace']}`",
        f"- Trading date: `{payload['trading_date']}`",
        f"- Day number: `{payload['day_number']}`",
        "",
        "## Safety Lock",
    ]
    for key, value in payload["safety_lock"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Required Script Check",
        f"- All required scripts present: `{payload['script_check']['all_required_scripts_present']}`",
        f"- Missing required scripts: `{payload['script_check']['missing_required_scripts']}`",
        "",
        "## One-Click Manual Launcher",
        f"- Launcher emitted: `{payload['one_click_launcher_emitted']}`",
        f"- Launcher path: `{payload.get('one_click_launcher_path', '')}`",
        "",
        "## Safe Command Sequence",
    ])
    for command in payload["safe_command_sequence"]:
        lines.append(f"{command['step']}. **{command['name']}** — {command['purpose']}")
        lines.append(f"   - Command: `{command['command']}`")
        lines.append(f"   - External API: `{command['executes_external_api']}` | Order API: `{command['executes_order_api']}` | Auto trading: `{command['starts_auto_trading']}`")
    lines.extend([
        "",
        "## Decision Notes",
        "- This pack prepares/runs local paper workflow commands only.",
        "- It does not create trades and does not tune the candidate.",
        "- No-trade days remain observed session days only; they do not count toward 30 valid trade-days.",
        "- Real money is never automatic and requires future explicit manual review/approval.",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(payload: Dict[str, Any], workspace: Path) -> Dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / "HQE_MANUAL_DAILY_LAUNCH_COMMAND_PACK.json"
    md_path = workspace / "HQE_MANUAL_DAILY_LAUNCH_COMMAND_PACK.md"
    csv_path = workspace / "HQE_MANUAL_DAILY_LAUNCH_COMMAND_PACK_STEPS.csv"
    launcher_path = workspace / "RUN_HQE_DAILY_SAFE_LAUNCH.ps1"

    payload = dict(payload)
    payload["one_click_launcher_emitted"] = True
    payload["one_click_launcher_path"] = str(launcher_path)

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")
    launcher_path.write_text(
        build_launcher_text(payload["safe_command_sequence"], workspace, payload["trading_date"], int(payload["day_number"])),
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "name", "purpose", "command", "executes_external_api", "executes_order_api", "starts_auto_trading"])
        writer.writeheader()
        for command in payload["safe_command_sequence"]:
            writer.writerow(command)

    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "csv": str(csv_path),
        "launcher": str(launcher_path),
    }


def build_launch_pack(repo_root: Path, workspace: Path, trading_date: str, day_number: int, write: bool = False) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    workspace = workspace.resolve()
    script_check = check_required_scripts(repo_root)
    commands = build_safe_commands(repo_root, workspace, trading_date, day_number)
    blocked_hits = detect_blocked_tokens(commands)

    launch_pack_status = "PASS" if script_check["all_required_scripts_present"] and not blocked_hits else "BLOCKED"
    decision = "SAFE_DAILY_LAUNCH_PACK_READY_MANUAL_LOGIN_REQUIRED" if launch_pack_status == "PASS" else "SAFE_DAILY_LAUNCH_PACK_NOT_READY"

    payload: Dict[str, Any] = {
        "version": VERSION,
        "launch_pack_status": launch_pack_status,
        "decision": decision,
        "created_time_utc": utc_now_iso(),
        "repo_root": str(repo_root),
        "workspace": str(workspace),
        "trading_date": trading_date,
        "day_number": day_number,
        "operator_mode": "MANUAL_ONE_CLICK_SAFE_LOCAL_RUN",
        "manual_login_required": True,
        "manual_operator_control_required": True,
        "one_click_launcher_emitted": False,
        "scheduled_task_installed_by_this_run": False,
        "external_api_calls_executed_by_launch_pack": False,
        "order_api_invoked_by_launch_pack": False,
        "broker_execution_invoked_by_launch_pack": False,
        "auto_trading_started_by_launch_pack": False,
        "fake_trades_created_by_launch_pack": False,
        "candidate_tuning_by_launch_pack": False,
        "real_money_automatic": False,
        "valid_trade_day_target": 30,
        "no_trade_day_counts_toward_valid_trade_day_target": False,
        "script_check": script_check,
        "safe_command_sequence": commands,
        "blocked_command_token_hits": blocked_hits,
        "safety_lock": dict(SAFETY_LOCK),
        "notes": [
            "Launcher is local-only and paper-only.",
            "Manual login remains required before operator action.",
            "Fyers connector preflight remains data-only; no transport is started by this pack.",
            "Order APIs and broker execution remain blocked.",
            "No fake trades are created; actual trades must come only from real paper trade rows.",
        ],
    }

    if write:
        payload["evidence_files"] = write_outputs(payload, workspace)
        payload["one_click_launcher_emitted"] = True
        payload["one_click_launcher_path"] = payload["evidence_files"]["launcher"]
    else:
        payload["evidence_files"] = {}

    return payload


def guard_check() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "safety_lock": dict(SAFETY_LOCK),
        "blocked_command_tokens": list(BLOCKED_COMMAND_TOKENS),
        "external_api_calls_executed_by_guard_check": False,
        "order_api_invoked_by_guard_check": False,
        "broker_execution_invoked_by_guard_check": False,
        "auto_trading_started_by_guard_check": False,
        "fake_trades_created_by_guard_check": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQE Module 155 manual daily launch command pack")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace")
    parser.add_argument("--trading-date", default=DEFAULT_TRADING_DATE, help="Trading date YYYY-MM-DD")
    parser.add_argument("--day-number", type=int, default=DEFAULT_DAY_NUMBER, help="Forward validation day number")
    parser.add_argument("--repo-root", default=os.getcwd(), help="Repository root")
    parser.add_argument("--write", action="store_true", help="Write JSON/Markdown/CSV and launcher to workspace")
    parser.add_argument("--guard-check", action="store_true", help="Print guard check only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.guard_check:
        print(json.dumps(guard_check(), indent=2, sort_keys=True))
        return 0

    payload = build_launch_pack(
        repo_root=Path(args.repo_root),
        workspace=Path(args.workspace),
        trading_date=args.trading_date,
        day_number=args.day_number,
        write=args.write,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["launch_pack_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
