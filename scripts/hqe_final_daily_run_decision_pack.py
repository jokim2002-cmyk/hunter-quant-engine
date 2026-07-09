#!/usr/bin/env python3
"""
Module 154 — Final Daily Run Decision Pack / Operator Launch Validation.

Purpose:
- Validate the local HQE daily app flow is ready for a manual operator launch.
- Produce local evidence files before a daily paper-only run.
- Keep startup/login/manual-control boundaries explicit.

Safety lock:
- paper/simulation only
- no real money
- no broker execution
- no real orders
- no auto trading
- no option selling
- no external API calls from this decision pack
- no fake trades
- no candidate tuning during validation
- no profitability claim
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

VERSION = "MODULE_154_FINAL_DAILY_RUN_DECISION_PACK_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_LOGIN_CREDENTIAL_FILE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_LOCAL_LOGIN\hqe_local_login_credentials.json")
DEFAULT_SESSION_FILE_NAME = "HQE_LOCAL_LOGIN_SESSION.json"
DEFAULT_DECISION_JSON = "FINAL_DAILY_RUN_DECISION_PACK.json"
DEFAULT_DECISION_MD = "FINAL_DAILY_RUN_DECISION_PACK.md"
DEFAULT_LEDGER = "FINAL_DAILY_RUN_DECISION_PACK_LEDGER.csv"

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "data_only": True,
    "local_operator_launch_only": True,
    "manual_login_required": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api_calls_from_decision_pack": True,
    "no_plaintext_secret_storage": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}

REQUIRED_SCRIPT_CANDIDATES: Dict[str, List[str]] = {
    "local_login_shell": ["scripts/hqe_local_login_shell.py"],
    "fyers_data_only_connector": ["scripts/hqe_fyers_data_only_connector.py"],
    "market_session_supervisor": ["scripts/hqe_market_session_supervisor.py"],
    "paper_signal_no_trade_reason_engine": ["scripts/hqe_paper_signal_no_trade_reason_engine.py"],
    "valid_trade_day_tracker": ["scripts/hqe_30_valid_trade_day_tracker.py"],
    "final_daily_app_flow_integration_pack": ["scripts/hqe_final_daily_app_flow_integration_pack.py"],
    # Module 145 naming can vary in old local branches, so accept several safe names.
    "forward_validation_day_close_recorder": [
        "scripts/record_forward_validation_day_close.py",
        "scripts/hqe_forward_validation_day_close_recorder.py",
        "scripts/forward_validation_day_close_recorder.py",
        "scripts/hqe_forward_validation_day_ledger_closer.py",
    ],
}

REQUIRED_EVIDENCE_CANDIDATES: Dict[str, List[str]] = {
    "day_ledger": ["FORWARD_VALIDATION_DAY_LEDGER.csv"],
    "day_ledger_evaluation": ["FORWARD_VALIDATION_DAY_LEDGER_EVALUATION.json"],
    "fyers_data_only_connector_status": ["FYERS_DATA_ONLY_CONNECTOR_STATUS.json"],
    "final_daily_app_flow_integration_status": ["FINAL_DAILY_APP_FLOW_INTEGRATION_PACK.json"],
    "valid_trade_day_tracker_status": ["HQE_30_VALID_TRADE_DAY_TRACKER.json", "THIRTY_VALID_TRADE_DAY_TRACKER.json"],
}

BLOCKED_ACTIONS: List[str] = [
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json_file(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def safe_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "ok", "pass", "passed"}:
        return True
    if text in {"false", "0", "no", "n", "fail", "failed"}:
        return False
    return None


def first_existing(root: Path, candidates: Iterable[str]) -> Optional[str]:
    for rel in candidates:
        if (root / rel).exists():
            return rel
    return None


def evaluate_script_readiness(repo_root: Path) -> Dict[str, Any]:
    details: Dict[str, Any] = {}
    missing: List[str] = []
    present: List[str] = []

    for key, candidates in REQUIRED_SCRIPT_CANDIDATES.items():
        match = first_existing(repo_root, candidates)
        details[key] = {
            "required": True,
            "present": match is not None,
            "matched_path": match,
            "accepted_candidates": candidates,
        }
        if match:
            present.append(key)
        else:
            missing.append(key)

    return {
        "script_readiness_status": "PASS" if not missing else "MISSING_REQUIRED_SCRIPTS",
        "present_scripts": present,
        "missing_script_keys": missing,
        "details": details,
    }


def evaluate_evidence_readiness(workspace: Path) -> Dict[str, Any]:
    details: Dict[str, Any] = {}
    missing: List[str] = []
    present: List[str] = []

    for key, candidates in REQUIRED_EVIDENCE_CANDIDATES.items():
        match = first_existing(workspace, candidates)
        details[key] = {
            "required_for_best_evidence": True,
            "present": match is not None,
            "matched_path": str(workspace / match) if match else None,
            "accepted_candidates": candidates,
        }
        if match:
            present.append(key)
        else:
            missing.append(key)

    return {
        "evidence_readiness_status": "PASS" if not missing else "PARTIAL_EVIDENCE_AVAILABLE",
        "present_evidence_keys": present,
        "missing_evidence_keys": missing,
        "details": details,
    }


def evaluate_login_state(workspace: Path, credential_file: Path = DEFAULT_LOGIN_CREDENTIAL_FILE) -> Dict[str, Any]:
    session_file = workspace / DEFAULT_SESSION_FILE_NAME
    credential_exists = credential_file.exists()
    session = read_json_file(session_file)
    session_exists = session is not None

    authenticated = False
    session_status = "MISSING_SESSION"
    login_required = True

    if session_exists:
        candidates = [
            session.get("authenticated"),
            session.get("login_authenticated"),
            session.get("login_ok"),
            session.get("session_ok"),
        ]
        authenticated = any(safe_bool(v) is True for v in candidates)
        explicit_status = str(session.get("session_status") or session.get("login_status") or "").strip().upper()
        if authenticated or explicit_status in {"PASS", "LOGIN_PASS", "AUTHENTICATED", "SESSION_ACTIVE"}:
            authenticated = True
            session_status = "AUTHENTICATED_SESSION_FOUND"
            login_required = False
        else:
            session_status = "SESSION_FILE_FOUND_BUT_NOT_AUTHENTICATED"

    if not credential_exists:
        # Credential setup is not mandatory for this pack to run; it means the operator must set it up before login.
        credential_status = "CREDENTIAL_SETUP_REQUIRED"
    else:
        credential_status = "CREDENTIAL_FILE_PRESENT_OUTSIDE_REPO"

    return {
        "credential_exists": credential_exists,
        "credential_file": str(credential_file),
        "credential_status": credential_status,
        "session_exists": session_exists,
        "session_file": str(session_file),
        "session_status": session_status,
        "authenticated_session": authenticated,
        "manual_login_required_before_daily_run": login_required,
    }


def evaluate_runtime_guards() -> Dict[str, Any]:
    return {
        "guard_status": "PASS",
        "blocked_actions": {name: "HARD_BLOCKED" for name in BLOCKED_ACTIONS},
        "external_api_calls_executed_by_decision_pack": False,
        "order_api_invoked_by_decision_pack": False,
        "broker_execution_invoked_by_decision_pack": False,
        "auto_trading_started_by_decision_pack": False,
        "fake_trades_created_by_decision_pack": False,
        "candidate_tuning_performed_by_decision_pack": False,
        "real_money_automatic": False,
    }


def make_operator_next_steps(decision: str, login: Mapping[str, Any], scripts: Mapping[str, Any], evidence: Mapping[str, Any]) -> List[str]:
    steps: List[str] = []
    if login.get("manual_login_required_before_daily_run"):
        steps.append("Open HQE local login shell and complete manual login before daily paper-only flow.")
    if scripts.get("missing_script_keys"):
        steps.append("Do not launch daily flow until missing required scripts are restored in repo.")
    if evidence.get("missing_evidence_keys"):
        steps.append("Run the safe evidence/status generators so daily run starts with current local evidence.")
    if decision == "FINAL_DAILY_RUN_READY_AFTER_MANUAL_LOGIN":
        steps.append("After manual login, operator may run local paper-only daily workflow; no broker execution is allowed.")
    elif decision == "FINAL_DAILY_RUN_READY_MANUAL_OPERATOR_REQUIRED":
        steps.append("Operator review required before pressing any local launch command.")
    else:
        steps.append("Keep validation in HOLD state until required manual/operator prerequisites are complete.")
    return steps


@dataclass(frozen=True)
class DecisionPackConfig:
    repo_root: Path
    workspace: Path
    trading_date: Optional[str] = None
    day_number: Optional[int] = None
    write: bool = False


def build_decision_pack(config: DecisionPackConfig) -> Dict[str, Any]:
    repo_root = config.repo_root.resolve()
    workspace = config.workspace.resolve()
    scripts = evaluate_script_readiness(repo_root)
    evidence = evaluate_evidence_readiness(workspace)
    login = evaluate_login_state(workspace)
    guards = evaluate_runtime_guards()

    missing_scripts = scripts["missing_script_keys"]
    login_required = bool(login["manual_login_required_before_daily_run"])

    if missing_scripts:
        decision = "FINAL_DAILY_RUN_BLOCKED_MISSING_REQUIRED_SCRIPTS"
        launch_ready = False
    elif login_required:
        decision = "FINAL_DAILY_RUN_READY_MANUAL_LOGIN_REQUIRED"
        launch_ready = False
    else:
        decision = "FINAL_DAILY_RUN_READY_AFTER_MANUAL_LOGIN"
        launch_ready = True

    # Evidence can be partial without failing this pack because some evidence files are created during/after a run.
    validation_status = "PASS" if not missing_scripts else "FAIL"

    payload: Dict[str, Any] = {
        "version": VERSION,
        "decision_pack_status": validation_status,
        "decision": decision,
        "manual_operator_launch_ready": launch_ready,
        "trading_date": config.trading_date,
        "day_number": config.day_number,
        "workspace": str(workspace),
        "repo_root": str(repo_root),
        "generated_at_utc": utc_now_iso(),
        "script_readiness": scripts,
        "evidence_readiness": evidence,
        "login_state": login,
        "runtime_guards": guards,
        "safety_lock": dict(SAFETY_LOCK),
        "operator_next_steps": [],
        "daily_flow_summary": [
            "PC ON / Windows logon opens local HQE login/status gate only.",
            "Manual login is required before the daily paper-only workflow.",
            "Market session supervisor controls 09:15-15:30 status and reporting due state.",
            "Fyers connector remains data-only; order APIs are hard-blocked.",
            "Paper signal/no-trade reason engine records evidence and never creates fake trades.",
            "Day close recorder and 30 valid trade-day tracker update validation counters.",
            "Real money is never automatic and requires a future explicit manual review.",
        ],
        "notes": [
            "This pack does not connect to Fyers, does not start live data transport, and does not call any external API.",
            "This pack does not place, modify, cancel, or inspect broker orders/positions/funds.",
            "No-trade days remain observed session days only; they do not count toward 30 valid trade-days.",
        ],
    }
    payload["operator_next_steps"] = make_operator_next_steps(decision, login, scripts, evidence)
    return payload


def write_markdown(path: Path, payload: Mapping[str, Any]) -> None:
    lines = [
        "# HQE Final Daily Run Decision Pack",
        "",
        f"- Version: `{payload.get('version')}`",
        f"- Status: `{payload.get('decision_pack_status')}`",
        f"- Decision: `{payload.get('decision')}`",
        f"- Manual operator launch ready: `{payload.get('manual_operator_launch_ready')}`",
        f"- Trading date: `{payload.get('trading_date')}`",
        f"- Day number: `{payload.get('day_number')}`",
        f"- Workspace: `{payload.get('workspace')}`",
        "",
        "## Safety Lock",
    ]
    safety = payload.get("safety_lock", {})
    if isinstance(safety, Mapping):
        for key, value in safety.items():
            lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Script Readiness"])
    script_status = payload.get("script_readiness", {})
    if isinstance(script_status, Mapping):
        lines.append(f"- script_readiness_status: `{script_status.get('script_readiness_status')}`")
        lines.append(f"- missing_script_keys: `{script_status.get('missing_script_keys')}`")
    lines.extend(["", "## Evidence Readiness"])
    evidence = payload.get("evidence_readiness", {})
    if isinstance(evidence, Mapping):
        lines.append(f"- evidence_readiness_status: `{evidence.get('evidence_readiness_status')}`")
        lines.append(f"- missing_evidence_keys: `{evidence.get('missing_evidence_keys')}`")
    lines.extend(["", "## Login State"])
    login = payload.get("login_state", {})
    if isinstance(login, Mapping):
        lines.append(f"- credential_status: `{login.get('credential_status')}`")
        lines.append(f"- session_status: `{login.get('session_status')}`")
        lines.append(f"- manual_login_required_before_daily_run: `{login.get('manual_login_required_before_daily_run')}`")
    lines.extend(["", "## Operator Next Steps"])
    for step in payload.get("operator_next_steps", []):
        lines.append(f"- {step}")
    lines.extend(["", "## Notes"])
    for note in payload.get("notes", []):
        lines.append(f"- {note}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def append_ledger(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "generated_at_utc",
        "version",
        "decision_pack_status",
        "decision",
        "manual_operator_launch_ready",
        "trading_date",
        "day_number",
        "workspace",
        "manual_login_required_before_daily_run",
        "script_readiness_status",
        "evidence_readiness_status",
        "external_api_calls_executed_by_decision_pack",
        "order_api_invoked_by_decision_pack",
        "broker_execution_invoked_by_decision_pack",
        "auto_trading_started_by_decision_pack",
        "fake_trades_created_by_decision_pack",
        "real_money_automatic",
    ]
    login = payload.get("login_state", {}) if isinstance(payload.get("login_state"), Mapping) else {}
    scripts = payload.get("script_readiness", {}) if isinstance(payload.get("script_readiness"), Mapping) else {}
    evidence = payload.get("evidence_readiness", {}) if isinstance(payload.get("evidence_readiness"), Mapping) else {}
    guards = payload.get("runtime_guards", {}) if isinstance(payload.get("runtime_guards"), Mapping) else {}
    row = {
        "generated_at_utc": payload.get("generated_at_utc"),
        "version": payload.get("version"),
        "decision_pack_status": payload.get("decision_pack_status"),
        "decision": payload.get("decision"),
        "manual_operator_launch_ready": payload.get("manual_operator_launch_ready"),
        "trading_date": payload.get("trading_date"),
        "day_number": payload.get("day_number"),
        "workspace": payload.get("workspace"),
        "manual_login_required_before_daily_run": login.get("manual_login_required_before_daily_run"),
        "script_readiness_status": scripts.get("script_readiness_status"),
        "evidence_readiness_status": evidence.get("evidence_readiness_status"),
        "external_api_calls_executed_by_decision_pack": guards.get("external_api_calls_executed_by_decision_pack"),
        "order_api_invoked_by_decision_pack": guards.get("order_api_invoked_by_decision_pack"),
        "broker_execution_invoked_by_decision_pack": guards.get("broker_execution_invoked_by_decision_pack"),
        "auto_trading_started_by_decision_pack": guards.get("auto_trading_started_by_decision_pack"),
        "fake_trades_created_by_decision_pack": guards.get("fake_trades_created_by_decision_pack"),
        "real_money_automatic": guards.get("real_money_automatic"),
    }
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def write_outputs(workspace: Path, payload: Mapping[str, Any]) -> Dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / DEFAULT_DECISION_JSON
    md_path = workspace / DEFAULT_DECISION_MD
    ledger_path = workspace / DEFAULT_LEDGER
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(md_path, payload)
    append_ledger(ledger_path, payload)
    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "ledger": str(ledger_path),
    }


def run_guard_check() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "safety_lock": dict(SAFETY_LOCK),
        "blocked_actions": {name: "HARD_BLOCKED" for name in BLOCKED_ACTIONS},
        "external_api_calls_executed_by_decision_pack": False,
        "order_api_invoked_by_decision_pack": False,
        "broker_execution_invoked_by_decision_pack": False,
        "auto_trading_started_by_decision_pack": False,
        "fake_trades_created_by_decision_pack": False,
        "candidate_tuning_performed_by_decision_pack": False,
        "real_money_automatic": False,
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQE Module 154 final daily run decision pack")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    parser.add_argument("--trading-date", default=None)
    parser.add_argument("--day-number", type=int, default=None)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.guard_check:
        print(json.dumps(run_guard_check(), indent=2, sort_keys=True))
        return 0

    config = DecisionPackConfig(
        repo_root=Path(args.repo_root),
        workspace=Path(args.workspace),
        trading_date=args.trading_date,
        day_number=args.day_number,
        write=args.write,
    )
    payload = build_decision_pack(config)
    if args.write:
        payload["evidence_files"] = write_outputs(config.workspace, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["decision_pack_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
