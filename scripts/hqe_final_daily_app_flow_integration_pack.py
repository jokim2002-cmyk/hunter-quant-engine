#!/usr/bin/env python3
"""HQE Module 153 - Final Daily App Flow Integration Pack.

This module wires the safe local daily HQE app flow together without enabling
broker execution, order APIs, auto trading, external API calls, option selling,
or fake trades.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "MODULE_153_FINAL_DAILY_APP_FLOW_INTEGRATION_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")

SAFETY_LOCK: dict[str, bool] = {
    "paper_only": True,
    "data_only": True,
    "local_flow_only": True,
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
    "real_money_requires_future_manual_review": True,
}

BLOCKED_CAPABILITIES = [
    "broker_order_execution",
    "place_order",
    "modify_order",
    "cancel_order",
    "exit_position",
    "option_selling",
    "auto_trading",
    "real_money_mode",
    "fake_trade_generation",
    "candidate_tuning_during_validation",
]

# Required scripts from Modules 147-152. These are local scripts only.
FLOW_STEPS: list[dict[str, Any]] = [
    {
        "step_id": "01_LOGIN_STATUS_GATE",
        "title": "Local HQE login/status gate",
        "script": "scripts/hqe_local_login_shell.py",
        "required": True,
        "safe_to_execute": True,
        "args_template": ["--status"],
        "auto_trade_capability": False,
        "external_api_capability": False,
        "broker_execution_capability": False,
    },
    {
        "step_id": "02_MARKET_SESSION_SUPERVISOR",
        "title": "Market session supervisor 09:15-15:30",
        "script": "scripts/hqe_market_session_supervisor.py",
        "required": True,
        "safe_to_execute": True,
        "args_template": ["--workspace", "{workspace}", "--write"],
        "auto_trade_capability": False,
        "external_api_capability": False,
        "broker_execution_capability": False,
    },
    {
        "step_id": "03_FYERS_DATA_ONLY_PREFLIGHT",
        "title": "Fyers data-only preflight guard",
        "script": "scripts/hqe_fyers_data_only_connector.py",
        "required": True,
        "safe_to_execute": True,
        "args_template": ["--preflight", "--workspace", "{workspace}", "--write"],
        "auto_trade_capability": False,
        "external_api_capability": False,
        "broker_execution_capability": False,
    },
    {
        "step_id": "04_PAPER_SIGNAL_NO_TRADE_REASON",
        "title": "Paper signal + no-trade reason engine",
        "script": "scripts/hqe_paper_signal_no_trade_reason_engine.py",
        "required": True,
        "safe_to_execute": True,
        "args_template": ["--workspace", "{workspace}", "--trading-date", "{trading_date}", "--day-number", "{day_number}", "--write"],
        "auto_trade_capability": False,
        "external_api_capability": False,
        "broker_execution_capability": False,
    },
    {
        "step_id": "05_DAY_CLOSE_RECORDER",
        "title": "Forward validation day close recorder",
        "script_candidates": [
            "scripts/hqe_forward_validation_day_close_recorder.py",
            "scripts/forward_validation_day_close_recorder.py",
            "scripts/record_forward_validation_day_close.py",
            "scripts/hqe_forward_validation_day_ledger_closer.py",
        ],
        "required": False,
        "safe_to_execute": False,
        "args_template": [],
        "auto_trade_capability": False,
        "external_api_capability": False,
        "broker_execution_capability": False,
    },
    {
        "step_id": "06_DAY_LEDGER_EVALUATOR",
        "title": "Forward validation day-ledger evaluator",
        "script": "scripts/evaluate_forward_validation_day_ledger.py",
        "required": True,
        "safe_to_execute": True,
        "args_template": ["--workspace", "{workspace}", "--write"],
        "auto_trade_capability": False,
        "external_api_capability": False,
        "broker_execution_capability": False,
    },
    {
        "step_id": "07_30_VALID_TRADE_DAY_TRACKER",
        "title": "30 valid trade-day validation tracker",
        "script": "scripts/hqe_30_valid_trade_day_tracker.py",
        "required": True,
        "safe_to_execute": True,
        "args_template": ["--workspace", "{workspace}", "--write"],
        "auto_trade_capability": False,
        "external_api_capability": False,
        "broker_execution_capability": False,
    },
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_trading_date() -> str:
    # Local machine date is sufficient here; this module does not fetch network time.
    return datetime.now().date().isoformat()


def resolve_script_path(repo_root: Path, step: dict[str, Any]) -> tuple[str | None, bool, list[str]]:
    checked: list[str] = []
    if "script" in step:
        rel = str(step["script"])
        checked.append(rel)
        return (rel, (repo_root / rel).exists(), checked)
    for rel in step.get("script_candidates", []):
        checked.append(str(rel))
        if (repo_root / str(rel)).exists():
            return (str(rel), True, checked)
    return (None, False, checked)


def render_args(args_template: list[str], workspace: Path, trading_date: str, day_number: int) -> list[str]:
    values = {
        "workspace": str(workspace),
        "trading_date": trading_date,
        "day_number": str(day_number),
    }
    return [str(item).format(**values) for item in args_template]


def build_flow_plan(
    repo_root: Path,
    workspace: Path,
    trading_date: str,
    day_number: int,
    execute_approved_local_steps: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    workspace = workspace.resolve()
    missing_required: list[str] = []
    missing_optional: list[str] = []
    planned_steps: list[dict[str, Any]] = []

    for step in FLOW_STEPS:
        rel_script, exists, checked = resolve_script_path(repo_root, step)
        required = bool(step.get("required", False))
        args = render_args(list(step.get("args_template", [])), workspace, trading_date, day_number)
        can_execute = bool(step.get("safe_to_execute", False)) and exists and not any(
            bool(step.get(key, False))
            for key in ["auto_trade_capability", "external_api_capability", "broker_execution_capability"]
        )
        if not exists:
            if required:
                missing_required.append(step["step_id"])
            else:
                missing_optional.append(step["step_id"])

        planned_steps.append(
            {
                "step_id": step["step_id"],
                "title": step["title"],
                "script": rel_script,
                "checked_scripts": checked,
                "script_exists": exists,
                "required": required,
                "safe_to_execute": bool(step.get("safe_to_execute", False)),
                "execution_approved_for_this_run": bool(execute_approved_local_steps and can_execute),
                "args": args,
                "auto_trade_capability": bool(step.get("auto_trade_capability", False)),
                "external_api_capability": bool(step.get("external_api_capability", False)),
                "broker_execution_capability": bool(step.get("broker_execution_capability", False)),
            }
        )

    integration_status = "PASS" if not missing_required else "FAIL_MISSING_REQUIRED_FLOW_STEPS"
    decision = (
        "FINAL_DAILY_APP_FLOW_READY_MANUAL_LOGIN_REQUIRED"
        if integration_status == "PASS"
        else "FINAL_DAILY_APP_FLOW_NOT_READY_FIX_MISSING_STEPS"
    )

    return {
        "version": VERSION,
        "integration_status": integration_status,
        "decision": decision,
        "generated_at_utc": utc_now_iso(),
        "repo_root": str(repo_root),
        "workspace": str(workspace),
        "trading_date": trading_date,
        "day_number": day_number,
        "daily_flow": [
            "PC_ON",
            "HQE_STARTUP_LOGIN_GATE_OPEN",
            "USER_LOCAL_LOGIN_REQUIRED",
            "LOCAL_OPERATOR_CONTROL_CENTER",
            "MARKET_SESSION_SUPERVISOR_0915_1530",
            "FYERS_DATA_ONLY_PREFLIGHT_NO_ORDER_API",
            "PAPER_SIGNAL_OR_NO_TRADE_REASON_ENGINE",
            "DAY_CLOSE_RECORDER_ZERO_TRADE_ALLOWED",
            "DAY_LEDGER_EVALUATOR_OBSERVED_VS_VALID_DAYS",
            "THIRTY_VALID_TRADE_DAY_TRACKER",
            "DAILY_REPORT_EVIDENCE_PACK",
        ],
        "planned_steps": planned_steps,
        "missing_required_steps": missing_required,
        "missing_optional_steps": missing_optional,
        "execute_approved_local_steps_requested": bool(execute_approved_local_steps),
        "external_api_calls_executed_by_integration_pack": False,
        "order_api_invoked_by_integration_pack": False,
        "broker_execution_invoked_by_integration_pack": False,
        "auto_trading_started_by_integration_pack": False,
        "fake_trades_created_by_integration_pack": False,
        "real_money_automatic": False,
        "safety_lock": SAFETY_LOCK.copy(),
        "blocked_capabilities": list(BLOCKED_CAPABILITIES),
    }


def execute_local_steps(plan: dict[str, Any]) -> dict[str, Any]:
    repo_root = Path(plan["repo_root"])
    execution_results: list[dict[str, Any]] = []
    for step in plan["planned_steps"]:
        if not step.get("execution_approved_for_this_run"):
            execution_results.append(
                {
                    "step_id": step["step_id"],
                    "execution_status": "SKIPPED_NOT_APPROVED_OR_NOT_SAFE",
                    "returncode": None,
                }
            )
            continue
        script = step.get("script")
        if not script:
            execution_results.append(
                {"step_id": step["step_id"], "execution_status": "SKIPPED_SCRIPT_NOT_FOUND", "returncode": None}
            )
            continue
        cmd = [sys.executable, str(repo_root / script)] + list(step.get("args", []))
        proc = subprocess.run(cmd, cwd=str(repo_root), text=True, capture_output=True)
        execution_results.append(
            {
                "step_id": step["step_id"],
                "execution_status": "PASS" if proc.returncode == 0 else "FAIL",
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-1200:],
                "stderr_tail": proc.stderr[-1200:],
            }
        )
    plan["execution_results"] = execution_results
    plan["executed_local_step_count"] = sum(1 for row in execution_results if row.get("execution_status") == "PASS")
    if any(row.get("execution_status") == "FAIL" for row in execution_results):
        plan["integration_status"] = "FAIL_LOCAL_STEP_EXECUTION"
        plan["decision"] = "FINAL_DAILY_APP_FLOW_NOT_READY_FIX_LOCAL_STEP_FAILURE"
    return plan


def guard_check() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "blocked_capabilities": {name: "HARD_BLOCKED" for name in BLOCKED_CAPABILITIES},
        "startup_auto_trading": False,
        "startup_auto_broker_connect": False,
        "startup_order_api": False,
        "real_money_automatic": False,
        "external_api_calls_executed": False,
        "order_api_invoked": False,
        "safety_lock": SAFETY_LOCK.copy(),
    }


def write_outputs(workspace: Path, payload: dict[str, Any]) -> dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / "HQE_FINAL_DAILY_APP_FLOW_INTEGRATION_STATUS.json"
    md_path = workspace / "HQE_FINAL_DAILY_APP_FLOW_INTEGRATION_STATUS.md"
    ledger_path = workspace / "HQE_FINAL_DAILY_APP_FLOW_INTEGRATION_LEDGER.csv"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# HQE Final Daily App Flow Integration Status",
        "",
        f"- version: {payload['version']}",
        f"- integration_status: {payload['integration_status']}",
        f"- decision: {payload['decision']}",
        f"- trading_date: {payload['trading_date']}",
        f"- day_number: {payload['day_number']}",
        f"- workspace: {payload['workspace']}",
        "",
        "## Safety Lock",
    ]
    for key, value in payload["safety_lock"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Flow Steps"])
    for step in payload["planned_steps"]:
        lines.append(
            f"- {step['step_id']}: {step['title']} | exists={step['script_exists']} | "
            f"approved={step['execution_approved_for_this_run']} | script={step['script']}"
        )
    lines.extend(["", "## Daily Flow"])
    for item in payload["daily_flow"]:
        lines.append(f"- {item}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    new_file = not ledger_path.exists()
    with ledger_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "generated_at_utc",
                "trading_date",
                "day_number",
                "integration_status",
                "decision",
                "missing_required_steps",
                "missing_optional_steps",
                "execute_requested",
                "executed_local_step_count",
                "real_money_automatic",
            ],
        )
        if new_file:
            writer.writeheader()
        writer.writerow(
            {
                "generated_at_utc": payload["generated_at_utc"],
                "trading_date": payload["trading_date"],
                "day_number": payload["day_number"],
                "integration_status": payload["integration_status"],
                "decision": payload["decision"],
                "missing_required_steps": ";".join(payload.get("missing_required_steps", [])),
                "missing_optional_steps": ";".join(payload.get("missing_optional_steps", [])),
                "execute_requested": str(payload.get("execute_approved_local_steps_requested", False)),
                "executed_local_step_count": str(payload.get("executed_local_step_count", 0)),
                "real_money_automatic": str(payload.get("real_money_automatic", False)),
            }
        )

    return {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQE final daily app flow integration pack")
    parser.add_argument("--repo-root", default=str(Path.cwd()), help="HQE repo root")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Active forward validation workspace")
    parser.add_argument("--trading-date", default=default_trading_date(), help="Trading date YYYY-MM-DD")
    parser.add_argument("--day-number", type=int, default=1, help="Forward validation day number")
    parser.add_argument("--write", action="store_true", help="Write JSON/MD/ledger evidence files")
    parser.add_argument(
        "--execute-approved-local-steps",
        action="store_true",
        help="Execute approved local-only status/report steps. Does not execute broker/order/API actions.",
    )
    parser.add_argument("--guard-check", action="store_true", help="Print safety guard status and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.guard_check:
        print(json.dumps(guard_check(), indent=2, sort_keys=True))
        return 0

    workspace = Path(args.workspace)
    payload = build_flow_plan(
        repo_root=Path(args.repo_root),
        workspace=workspace,
        trading_date=str(args.trading_date),
        day_number=int(args.day_number),
        execute_approved_local_steps=bool(args.execute_approved_local_steps),
    )
    if args.execute_approved_local_steps and payload["integration_status"] == "PASS":
        payload = execute_local_steps(payload)
    if args.write:
        payload["evidence_files"] = write_outputs(workspace, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["integration_status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
