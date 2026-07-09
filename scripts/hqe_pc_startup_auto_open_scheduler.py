#!/usr/bin/env python3
"""HQE Module 152: PC Startup / HQE Auto Open Scheduler.

This module creates a safe local Windows startup scheduler foundation.
It does NOT place orders, does NOT connect to broker APIs, does NOT auto trade,
and does NOT store secrets. The planned startup action opens the local HQE login
/status gate only. Any paper workflow remains behind local login/manual operator
control.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "MODULE_152_PC_STARTUP_AUTO_OPEN_SCHEDULER_V1"
DEFAULT_WORKSPACE = Path(
    r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"
)
TASK_NAME = "HQE_Local_Login_Gate_Startup_PaperOnly"
STARTUP_LAUNCHER_NAME = "HQE_STARTUP_OPEN_LOGIN_GATE_PAPER_ONLY.ps1"
TASK_COMMANDS_NAME = "HQE_INSTALL_STARTUP_LOGIN_GATE_TASK_COMMANDS.ps1"
STATUS_JSON_NAME = "HQE_PC_STARTUP_AUTO_OPEN_SCHEDULER_STATUS.json"
STATUS_MD_NAME = "HQE_PC_STARTUP_AUTO_OPEN_SCHEDULER_STATUS.md"
LEDGER_NAME = "HQE_PC_STARTUP_AUTO_OPEN_SCHEDULER_LEDGER.csv"

SAFETY_LOCK = {
    "paper_only": True,
    "local_login_gate_only": True,
    "opens_hqe_login_shell": True,
    "requires_operator_login": True,
    "requires_manual_operator_control": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api_on_startup": True,
    "no_plaintext_secret_storage": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}

BLOCKED_STARTUP_ACTIONS = [
    "place_order",
    "modify_order",
    "cancel_order",
    "exit_positions",
    "auto_trade",
    "broker_execute",
    "connect_order_api",
    "sell_option",
    "store_plaintext_secret",
    "tune_candidate",
    "fake_trade",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo_path(repo: str | None) -> Path:
    if repo:
        return Path(repo).resolve()
    return Path.cwd().resolve()


def _workspace_path(workspace: str | None) -> Path:
    return Path(workspace).resolve() if workspace else DEFAULT_WORKSPACE


def _quote_ps(value: str) -> str:
    return value.replace("'", "''")


def _safe_windows_path(path: Path) -> str:
    return str(path).replace("/", "\\")


def build_startup_launcher(repo_path: Path, workspace: Path) -> str:
    repo = _quote_ps(_safe_windows_path(repo_path))
    workspace_value = _quote_ps(_safe_windows_path(workspace))
    return f"""# HQE Module 152 startup launcher
# Safety: local login gate/status only. No broker execution. No orders. No auto trading.
$ErrorActionPreference = 'Stop'
$RepoPath = '{repo}'
$Workspace = '{workspace_value}'
$Py = Join-Path $RepoPath '.venv\\Scripts\\python.exe'
$LoginShell = Join-Path $RepoPath 'scripts\\hqe_local_login_shell.py'

Write-Host '============================================================'
Write-Host 'HQE LOCAL LOGIN GATE - PAPER ONLY'
Write-Host '============================================================'
Write-Host 'Safety: paper-only, no real money, no broker execution, no real orders, no auto trading.'
Write-Host ''

if (!(Test-Path $RepoPath)) {{ throw "Repo path not found: $RepoPath" }}
if (!(Test-Path $Py)) {{ throw "Python venv not found: $Py" }}
if (!(Test-Path $LoginShell)) {{ throw "Login shell script not found: $LoginShell" }}

Set-Location $RepoPath
& $Py $LoginShell --status --workspace $Workspace

Write-Host ''
Write-Host 'Startup opened HQE local login gate/status only.'
Write-Host 'After login, operator must manually start paper workflow from HQE control center.'
Write-Host 'No order API, broker execution, real orders, or auto trading is started here.'
Write-Host ''
Write-Host 'Keep this window open for operator review, or close it if not trading today.'
Read-Host 'Press Enter to close'
"""


def build_task_commands(repo_path: Path, workspace: Path) -> str:
    launcher = workspace / STARTUP_LAUNCHER_NAME
    launcher_win = _safe_windows_path(launcher)
    task_name = TASK_NAME
    escaped_launcher = launcher_win.replace('"', '\\"')
    task_run = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{escaped_launcher}"'
    return f"""# HQE Module 152 optional Windows Task Scheduler commands
# This file is generated for manual operator use only.
# It opens the local HQE login/status gate at Windows logon.
# It does NOT start broker execution, real orders, order APIs, or auto trading.

$TaskName = '{task_name}'
$TaskRun = '{_quote_ps(task_run)}'

Write-Host 'HQE optional startup scheduler commands - paper-only login gate.'
Write-Host 'Review before running. This is local-only and does not connect/order/trade.'
Write-Host ''
Write-Host 'Install command:'
Write-Host "schtasks /Create /TN `"$TaskName`" /SC ONLOGON /TR `"$TaskRun`" /RL LIMITED /F"
Write-Host ''
Write-Host 'Uninstall command:'
Write-Host "schtasks /Delete /TN `"$TaskName`" /F"
Write-Host ''
Write-Host 'To install manually, copy the Install command above into an Administrator PowerShell only after review.'
"""


def build_plan(repo_path: Path, workspace: Path) -> dict[str, Any]:
    launcher_path = workspace / STARTUP_LAUNCHER_NAME
    task_commands_path = workspace / TASK_COMMANDS_NAME
    task_action = (
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
        f'"{_safe_windows_path(launcher_path)}"'
    )
    return {
        "version": VERSION,
        "scheduler_status": "PASS",
        "scheduler_mode": "LOCAL_STARTUP_LOGIN_GATE_ONLY",
        "startup_trigger": "WINDOWS_ONLOGON",
        "task_name": TASK_NAME,
        "task_action_preview": task_action,
        "startup_action": "OPEN_LOCAL_HQE_LOGIN_STATUS_GATE_ONLY",
        "repo_path": _safe_windows_path(repo_path),
        "workspace": _safe_windows_path(workspace),
        "launcher_path": _safe_windows_path(launcher_path),
        "task_commands_path": _safe_windows_path(task_commands_path),
        "scheduled_task_installed_by_this_run": False,
        "requires_operator_login": True,
        "requires_manual_operator_control": True,
        "auto_start_trading": False,
        "auto_broker_connect": False,
        "auto_order_execution": False,
        "external_api_calls_executed": False,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "plaintext_secrets_written": False,
        "candidate_tuning": False,
        "fake_trades_created": False,
        "allowed_startup_step": "open_local_login_shell_status_only",
        "blocked_startup_actions": BLOCKED_STARTUP_ACTIONS,
        "safety_lock": dict(SAFETY_LOCK),
        "decision": "STARTUP_LOGIN_GATE_PLAN_READY_MANUAL_INSTALL_REQUIRED",
        "notes": [
            "Generated startup plan opens HQE local login/status gate only.",
            "Windows scheduled task installation is manual; this run does not modify OS scheduler.",
            "After login, operator must manually start the paper-only workflow/control center.",
            "No broker execution, order API, real orders, auto trading, or option selling is started at PC boot.",
        ],
        "generated_at_utc": _utc_now_iso(),
    }


def validate_plan(plan: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    safety = plan.get("safety_lock", {})
    for key, expected in SAFETY_LOCK.items():
        if safety.get(key) is not expected:
            warnings.append(f"SAFETY_LOCK_MISMATCH:{key}")
    forbidden_truthy = [
        "auto_start_trading",
        "auto_broker_connect",
        "auto_order_execution",
        "external_api_calls_executed",
        "order_api_invoked",
        "broker_execution_invoked",
        "plaintext_secrets_written",
        "candidate_tuning",
        "fake_trades_created",
        "scheduled_task_installed_by_this_run",
    ]
    for key in forbidden_truthy:
        if plan.get(key) is not False:
            warnings.append(f"FORBIDDEN_STARTUP_FLAG_TRUE:{key}")
    if plan.get("startup_action") != "OPEN_LOCAL_HQE_LOGIN_STATUS_GATE_ONLY":
        warnings.append("UNEXPECTED_STARTUP_ACTION")
    if plan.get("startup_trigger") != "WINDOWS_ONLOGON":
        warnings.append("UNEXPECTED_STARTUP_TRIGGER")
    return warnings


def write_outputs(plan: dict[str, Any], repo_path: Path, workspace: Path) -> dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    launcher_path = workspace / STARTUP_LAUNCHER_NAME
    commands_path = workspace / TASK_COMMANDS_NAME
    json_path = workspace / STATUS_JSON_NAME
    md_path = workspace / STATUS_MD_NAME
    ledger_path = workspace / LEDGER_NAME

    launcher_path.write_text(build_startup_launcher(repo_path, workspace), encoding="utf-8")
    commands_path.write_text(build_task_commands(repo_path, workspace), encoding="utf-8")
    json_path.write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(plan), encoding="utf-8")
    append_ledger(ledger_path, plan)

    return {
        "launcher": _safe_windows_path(launcher_path),
        "task_commands": _safe_windows_path(commands_path),
        "json": _safe_windows_path(json_path),
        "markdown": _safe_windows_path(md_path),
        "ledger": _safe_windows_path(ledger_path),
    }


def append_ledger(path: Path, plan: dict[str, Any]) -> None:
    fieldnames = [
        "generated_at_utc",
        "version",
        "scheduler_status",
        "scheduler_mode",
        "startup_trigger",
        "task_name",
        "startup_action",
        "requires_operator_login",
        "requires_manual_operator_control",
        "auto_start_trading",
        "auto_broker_connect",
        "auto_order_execution",
        "external_api_calls_executed",
        "order_api_invoked",
        "broker_execution_invoked",
        "plaintext_secrets_written",
        "decision",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({key: plan.get(key, "") for key in fieldnames})


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# HQE PC Startup Auto Open Scheduler",
        "",
        f"- Version: `{plan['version']}`",
        f"- Scheduler status: `{plan['scheduler_status']}`",
        f"- Mode: `{plan['scheduler_mode']}`",
        f"- Startup trigger: `{plan['startup_trigger']}`",
        f"- Startup action: `{plan['startup_action']}`",
        f"- Decision: `{plan['decision']}`",
        "",
        "## Counters / flags",
        "",
        f"- Requires operator login: `{plan['requires_operator_login']}`",
        f"- Requires manual operator control: `{plan['requires_manual_operator_control']}`",
        f"- Auto start trading: `{plan['auto_start_trading']}`",
        f"- Auto broker connect: `{plan['auto_broker_connect']}`",
        f"- Auto order execution: `{plan['auto_order_execution']}`",
        f"- External API calls executed: `{plan['external_api_calls_executed']}`",
        f"- Order API invoked: `{plan['order_api_invoked']}`",
        f"- Broker execution invoked: `{plan['broker_execution_invoked']}`",
        f"- Plaintext secrets written: `{plan['plaintext_secrets_written']}`",
        "",
        "## Safety lock",
        "",
    ]
    for key, value in plan["safety_lock"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Manual install note",
        "",
        "This module only generates a Windows startup plan and helper commands. It does not install the scheduled task by itself.",
        "Review the generated task commands manually before installing.",
        "",
    ])
    return "\n".join(lines)


def guard_check_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "scheduler_mode": "LOCAL_STARTUP_LOGIN_GATE_ONLY",
        "blocked_startup_actions": {action: "HARD_BLOCKED" for action in BLOCKED_STARTUP_ACTIONS},
        "auto_start_trading": False,
        "auto_broker_connect": False,
        "auto_order_execution": False,
        "external_api_calls_executed": False,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "plaintext_secrets_written": False,
        "safety_lock": dict(SAFETY_LOCK),
    }


def run_scheduler_plan(
    workspace: str | None = None,
    repo: str | None = None,
    write: bool = False,
) -> dict[str, Any]:
    repo_path = _repo_path(repo)
    workspace_path = _workspace_path(workspace)
    plan = build_plan(repo_path, workspace_path)
    warnings = validate_plan(plan)
    plan["warnings"] = warnings
    if warnings:
        plan["scheduler_status"] = "FAIL"
        plan["decision"] = "STARTUP_LOGIN_GATE_PLAN_BLOCKED_SAFETY_WARNING"
    if write:
        plan["evidence_files"] = write_outputs(plan, repo_path, workspace_path)
    return plan


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQE Module 152 PC startup login gate scheduler plan")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace path")
    parser.add_argument("--repo", default=None, help="Repo path; defaults to current working directory")
    parser.add_argument("--write", action="store_true", help="Write status/evidence/helper scripts to workspace")
    parser.add_argument("--guard-check", action="store_true", help="Print startup hard-block guard status")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.guard_check:
        print(json.dumps(guard_check_payload(), indent=2, sort_keys=True))
        return 0
    payload = run_scheduler_plan(workspace=args.workspace, repo=args.repo, write=args.write)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("scheduler_status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
