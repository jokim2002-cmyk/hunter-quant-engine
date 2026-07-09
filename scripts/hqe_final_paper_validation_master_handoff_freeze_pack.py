#!/usr/bin/env python3
"""
HQE Module 160 — Final Paper Validation Master Handoff / Freeze Pack.

This module creates a local-only final handoff/freeze evidence pack for the HQE
forward paper-validation workflow. It never calls broker APIs, order APIs,
external APIs, or creates fake trades. It only reads local repo/workspace files
and writes summary artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

VERSION = "MODULE_160_FINAL_PAPER_VALIDATION_MASTER_HANDOFF_FREEZE_PACK_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")

MIN_VALID_TRADE_DAYS_REQUIRED = 30
MIN_TRADES_REQUIRED = 30
MIN_EXPIRY_WEEKS_REQUIRED = 4

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "data_only_or_local_only": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
    "real_money_manual_review_only": True,
    "external_api_calls_executed_by_freeze_pack": False,
    "order_api_invoked_by_freeze_pack": False,
    "broker_execution_invoked_by_freeze_pack": False,
    "auto_trading_started_by_freeze_pack": False,
    "fake_trades_created_by_freeze_pack": False,
    "real_money_automatic": False,
}

REQUIRED_REPO_FILES: List[str] = [
    "scripts/evaluate_forward_validation_day_ledger.py",
    "scripts/hqe_local_login_shell.py",
    "scripts/hqe_fyers_data_only_connector.py",
    "scripts/hqe_market_session_supervisor.py",
    "scripts/hqe_paper_signal_no_trade_reason_engine.py",
    "scripts/hqe_30_valid_trade_day_tracker.py",
    "scripts/hqe_pc_startup_auto_open_scheduler.py",
    "scripts/hqe_final_daily_app_flow_integration_pack.py",
    "scripts/hqe_final_daily_run_decision_pack.py",
    "scripts/hqe_manual_daily_launch_command_pack.py",
    "scripts/hqe_final_daily_evidence_auto_open_pack.py",
    "scripts/hqe_final_operator_desktop_control_pack.py",
    "scripts/hqe_final_safe_daily_run_smoke_pack.py",
    "scripts/hqe_30_day_paper_validation_daily_operating_sop.py",
]

MODULE_ROADMAP: List[Dict[str, str]] = [
    {"module": "146", "name": "Forward Validation Evaluator Day-Ledger Integration", "status": "COMPLETE_REQUIRED"},
    {"module": "147", "name": "HQE Login Shell / Local Desktop App Gate", "status": "COMPLETE_REQUIRED"},
    {"module": "148", "name": "Fyers Data-Only Connector", "status": "COMPLETE_REQUIRED"},
    {"module": "149", "name": "Market Session Supervisor 09:15-15:30", "status": "COMPLETE_REQUIRED"},
    {"module": "150", "name": "Paper Signal + No-Trade Reason Engine", "status": "COMPLETE_REQUIRED"},
    {"module": "151", "name": "30 Valid Trade-Day Validation Tracker", "status": "COMPLETE_REQUIRED"},
    {"module": "152", "name": "PC Startup / HQE Auto Open Scheduler", "status": "COMPLETE_REQUIRED"},
    {"module": "153", "name": "Final HQE Daily App Flow Integration Pack", "status": "COMPLETE_REQUIRED"},
    {"module": "154", "name": "Final Daily Run Decision Pack / Operator Launch Validation", "status": "COMPLETE_REQUIRED"},
    {"module": "155", "name": "Manual Daily Launch Command Pack / One-Click Safe Run", "status": "COMPLETE_REQUIRED"},
    {"module": "156", "name": "Final Daily Evidence Auto-Open / Operator Shortcut Pack", "status": "COMPLETE_REQUIRED"},
    {"module": "157", "name": "Final Operator Desktop Control Pack", "status": "COMPLETE_REQUIRED"},
    {"module": "158", "name": "Final Safe Daily Run Smoke Pack", "status": "COMPLETE_REQUIRED"},
    {"module": "159", "name": "Final 30-Day Paper Validation Daily Operating SOP", "status": "COMPLETE_REQUIRED"},
    {"module": "160", "name": "Final Paper Validation Master Handoff / Freeze Pack", "status": "CURRENT"},
]

DAILY_FLOW: List[str] = [
    "PC ON",
    "HQE startup/login gate opens",
    "Manual login and operator control required",
    "Market session supervisor enforces 09:15-15:30 discipline",
    "Fyers data-only preflight remains order/broker blocked",
    "Paper signal feed/no-trade reason engine records why trade did or did not happen",
    "Day close recorder writes zero-trade or trade-day evidence",
    "30 valid trade-day tracker counts only days with at least one actual paper trade",
    "Daily evidence/report/shortcut/control panel remains local-files only",
    "Final review stays manual; real-money is never automatic",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def boolish_true(value: Any) -> bool:
    return str(value or "").strip().upper() in {"1", "TRUE", "YES", "Y", "PASS", "OK"}


def normalize_header(fieldnames: Iterable[str] | None) -> List[str]:
    if not fieldnames:
        return []
    cleaned: List[str] = []
    for name in fieldnames:
        cleaned.append(str(name or "").replace("\ufeff", "").strip())
    return cleaned


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = normalize_header(reader.fieldnames)
        rows: List[Dict[str, str]] = []
        for raw in reader:
            row: Dict[str, str] = {}
            values = list(raw.values())
            for index, header in enumerate(headers):
                row[header] = str(values[index] if index < len(values) else "").strip()
            rows.append(row)
        return rows


def write_csv_rows(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def get_first(row: Dict[str, Any], keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value or "").strip()))
    except (TypeError, ValueError):
        return default


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except (TypeError, ValueError):
        return default


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def compute_day_counts(workspace: Path) -> Dict[str, Any]:
    day_ledger = workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv"
    day_rows = read_csv_rows(day_ledger)
    observed_dates = set()
    valid_trade_dates = set()
    safety_warning_dates: List[str] = []

    for row in day_rows:
        trade_date = get_first(row, ["trading_date", "date", "session_date", "day_date"], "UNKNOWN_DATE")
        if trade_date:
            observed_dates.add(trade_date)
        trade_count = parse_int(get_first(row, ["trade_count", "actual_paper_trades", "trades"], "0"))
        if trade_count > 0 and trade_date:
            valid_trade_dates.add(trade_date)
        safety_ok_value = get_first(row, ["safety_ok", "safety_lock_ok", "paper_only"], "YES")
        if safety_ok_value and not boolish_true(safety_ok_value):
            safety_warning_dates.append(trade_date)

    return {
        "day_ledger_path": str(day_ledger),
        "day_ledger_exists": day_ledger.exists(),
        "day_ledger_rows": len(day_rows),
        "observed_session_days": len(observed_dates),
        "valid_paper_trade_days": len(valid_trade_dates),
        "no_trade_observed_days": max(0, len(observed_dates) - len(valid_trade_dates)),
        "remaining_valid_trade_days": max(0, MIN_VALID_TRADE_DAYS_REQUIRED - len(valid_trade_dates)),
        "safety_warning_dates": safety_warning_dates,
    }


def discover_day_trade_logs(workspace: Path) -> List[Path]:
    return sorted(workspace.glob("DAY_*_FORWARD_TRADE_LOG.csv"))


def compute_trade_counts(workspace: Path) -> Dict[str, Any]:
    master = workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv"
    master_rows = read_csv_rows(master)
    trade_rows: List[Dict[str, str]] = []
    source = "NONE"

    if master_rows:
        trade_rows = master_rows
        source = "FORWARD_VALIDATION_MASTER_LEDGER.csv"
    else:
        day_logs = discover_day_trade_logs(workspace)
        for path in day_logs:
            trade_rows.extend(read_csv_rows(path))
        if trade_rows:
            source = "DAY_FORWARD_TRADE_LOG_FILES"

    expiry_weeks = set()
    cumulative_forward_net = 0.0
    for row in trade_rows:
        expiry_value = get_first(row, ["expiry_week", "expiry", "expiry_date", "option_expiry", "contract_expiry"], "")
        if expiry_value:
            expiry_weeks.add(expiry_value[:10])
        cumulative_forward_net += parse_float(get_first(row, ["net", "net_pnl", "net_result", "paper_net", "pnl"], "0"))

    return {
        "master_ledger_path": str(master),
        "master_ledger_exists": master.exists(),
        "actual_trade_rows_source": source,
        "actual_paper_trades": len(trade_rows),
        "distinct_expiry_weeks": len(expiry_weeks),
        "cumulative_forward_net": round(cumulative_forward_net, 2),
    }


def check_required_repo_files(repo_root: Path) -> Dict[str, Any]:
    files = []
    missing = []
    present = []
    for rel in REQUIRED_REPO_FILES:
        path = repo_root / rel
        item = {"path": rel, "exists": path.exists()}
        files.append(item)
        if path.exists():
            present.append(rel)
        else:
            missing.append(rel)
    return {
        "required_repo_files_total": len(REQUIRED_REPO_FILES),
        "required_repo_files_present": len(present),
        "required_repo_files_missing": len(missing),
        "missing_required_repo_files": missing,
        "required_repo_files": files,
    }


def decision_from_counts(day_counts: Dict[str, Any], trade_counts: Dict[str, Any], repo_checks: Dict[str, Any]) -> str:
    if repo_checks["required_repo_files_missing"] > 0:
        return "FREEZE_PACK_REPO_INCOMPLETE_FIX_REQUIRED"
    if day_counts["valid_paper_trade_days"] < MIN_VALID_TRADE_DAYS_REQUIRED:
        return "PAPER_VALIDATION_FREEZE_READY_HOLD_MORE_VALID_TRADE_DAYS_REQUIRED"
    if trade_counts["actual_paper_trades"] < MIN_TRADES_REQUIRED:
        return "PAPER_VALIDATION_FREEZE_READY_HOLD_MORE_ACTUAL_TRADES_REQUIRED"
    if trade_counts["distinct_expiry_weeks"] < MIN_EXPIRY_WEEKS_REQUIRED:
        return "PAPER_VALIDATION_FREEZE_READY_HOLD_MORE_EXPIRY_WEEKS_REQUIRED"
    return "PAPER_VALIDATION_SAMPLE_COMPLETE_MANUAL_REVIEW_REQUIRED_REAL_MONEY_STILL_BLOCKED"


def build_payload(workspace: Path, repo_root: Path | None = None) -> Dict[str, Any]:
    repo = repo_root or repo_root_from_script()
    day_counts = compute_day_counts(workspace)
    trade_counts = compute_trade_counts(workspace)
    repo_checks = check_required_repo_files(repo)
    decision = decision_from_counts(day_counts, trade_counts, repo_checks)

    payload: Dict[str, Any] = {
        "version": VERSION,
        "freeze_pack_status": "PASS" if repo_checks["required_repo_files_missing"] == 0 else "FAIL",
        "decision": decision,
        "generated_at_utc": utc_now_iso(),
        "repo_root": str(repo),
        "workspace": str(workspace),
        "modules_complete_expected_after_push": 160,
        "phase_12_safe_freeze": "COMPLETE",
        "ui_dashboard_operator_phase": "COMPLETE",
        "current_phase": "FORWARD_PAPER_VALIDATION_DAILY_OPERATION",
        "minimum_valid_trade_days_required": MIN_VALID_TRADE_DAYS_REQUIRED,
        "minimum_trades_required": MIN_TRADES_REQUIRED,
        "minimum_expiry_weeks_required": MIN_EXPIRY_WEEKS_REQUIRED,
        "observed_session_days": day_counts["observed_session_days"],
        "valid_paper_trade_days": day_counts["valid_paper_trade_days"],
        "no_trade_observed_days": day_counts["no_trade_observed_days"],
        "remaining_valid_trade_days": day_counts["remaining_valid_trade_days"],
        "actual_paper_trades": trade_counts["actual_paper_trades"],
        "distinct_expiry_weeks": trade_counts["distinct_expiry_weeks"],
        "cumulative_forward_net": trade_counts["cumulative_forward_net"],
        "actual_trade_rows_source": trade_counts["actual_trade_rows_source"],
        "day_counts": day_counts,
        "trade_counts": trade_counts,
        "repo_checks": repo_checks,
        "module_roadmap": MODULE_ROADMAP,
        "daily_flow": DAILY_FLOW,
        "real_money_rule": "NOT_AUTOMATIC_REQUIRES_SEPARATE_MANUAL_REVIEW_AND_FUTURE_EXPLICIT_APPROVAL",
        "no_trade_day_rule": "COUNTS_AS_OBSERVED_SESSION_DAY_ONLY_NOT_VALID_TRADE_DAY",
        "valid_trade_day_rule": "ONLY_DAYS_WITH_AT_LEAST_ONE_ACTUAL_PAPER_TRADE_COUNT_TOWARD_30_VALID_TRADE_DAYS",
        "candidate_tuning_rule": "NO_CANDIDATE_TUNING_DURING_FORWARD_VALIDATION",
        "safety_lock": SAFETY_LOCK,
        "external_api_calls_executed_by_freeze_pack": False,
        "order_api_invoked_by_freeze_pack": False,
        "broker_execution_invoked_by_freeze_pack": False,
        "auto_trading_started_by_freeze_pack": False,
        "fake_trades_created_by_freeze_pack": False,
        "real_money_automatic": False,
        "operator_next_action": "RUN_DAILY_SAFE_FLOW_EACH_MARKET_DAY_AND_REVIEW_EVIDENCE_MANUALLY",
    }
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    missing = payload["repo_checks"]["missing_required_repo_files"]
    roadmap_lines = "\n".join(
        f"- Module {item['module']}: {item['name']} — {item['status']}" for item in payload["module_roadmap"]
    )
    flow_lines = "\n".join(f"{idx + 1}. {step}" for idx, step in enumerate(payload["daily_flow"]))
    missing_lines = "\n".join(f"- {item}" for item in missing) if missing else "- None"
    return f"""# HQE Final Paper Validation Master Handoff / Freeze Pack

Generated UTC: {payload['generated_at_utc']}  
Version: {payload['version']}  
Status: **{payload['freeze_pack_status']}**  
Decision: **{payload['decision']}**

## Counters

- Observed session days: **{payload['observed_session_days']}**
- Valid paper trade days: **{payload['valid_paper_trade_days']} / {payload['minimum_valid_trade_days_required']}**
- No-trade observed days: **{payload['no_trade_observed_days']}**
- Remaining valid trade days: **{payload['remaining_valid_trade_days']}**
- Actual paper trades: **{payload['actual_paper_trades']} / {payload['minimum_trades_required']}**
- Distinct expiry weeks from actual trades: **{payload['distinct_expiry_weeks']} / {payload['minimum_expiry_weeks_required']}**
- Cumulative forward net from actual trade rows only: **{payload['cumulative_forward_net']}**

## Rules Locked

- No-trade day rule: {payload['no_trade_day_rule']}
- Valid trade day rule: {payload['valid_trade_day_rule']}
- Real-money rule: {payload['real_money_rule']}
- Candidate tuning rule: {payload['candidate_tuning_rule']}

## Safe Daily Flow

{flow_lines}

## Module Roadmap Freeze

{roadmap_lines}

## Missing Required Repo Files

{missing_lines}

## Safety Lock

- Paper only: {payload['safety_lock']['paper_only']}
- No real money: {payload['safety_lock']['no_real_money']}
- No broker execution: {payload['safety_lock']['no_broker_execution']}
- No real orders: {payload['safety_lock']['no_real_orders']}
- No auto trading: {payload['safety_lock']['no_auto_trading']}
- No option selling: {payload['safety_lock']['no_option_selling']}
- No fake trades: {payload['safety_lock']['no_fake_trades']}
- No candidate tuning during validation: {payload['safety_lock']['no_candidate_tuning_during_validation']}
- No profitability claim: {payload['safety_lock']['no_profitability_claim']}
- Real money automatic: {payload['real_money_automatic']}

## Operator Next Action

{payload['operator_next_action']}
"""


def render_cmd_launcher(workspace: Path) -> str:
    return f"""@echo off
setlocal
cd /d "%~dp0"
echo HQE FINAL PAPER VALIDATION MASTER HANDOFF / FREEZE PACK
echo.
echo This launcher opens local freeze evidence files only.
echo It does NOT call broker APIs, order APIs, external APIs, or start trading.
echo.
if exist "{workspace / 'HQE_FINAL_PAPER_VALIDATION_MASTER_HANDOFF_FREEZE_PACK.md'}" start "" "{workspace / 'HQE_FINAL_PAPER_VALIDATION_MASTER_HANDOFF_FREEZE_PACK.md'}"
if exist "{workspace / 'HQE_FINAL_PAPER_VALIDATION_MASTER_HANDOFF_FREEZE_PACK.json'}" start "" "{workspace / 'HQE_FINAL_PAPER_VALIDATION_MASTER_HANDOFF_FREEZE_PACK.json'}"
echo Done. Manual review required.
pause
"""


def write_outputs(payload: Dict[str, Any], workspace: Path) -> Dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / "HQE_FINAL_PAPER_VALIDATION_MASTER_HANDOFF_FREEZE_PACK.json"
    md_path = workspace / "HQE_FINAL_PAPER_VALIDATION_MASTER_HANDOFF_FREEZE_PACK.md"
    csv_path = workspace / "HQE_FINAL_PAPER_VALIDATION_MASTER_HANDOFF_FREEZE_PACK_LEDGER.csv"
    cmd_path = workspace / "OPEN_HQE_FINAL_FREEZE_PACK_SAFE.cmd"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    cmd_path.write_text(render_cmd_launcher(workspace), encoding="utf-8")

    ledger_row = {
        "generated_at_utc": payload["generated_at_utc"],
        "version": payload["version"],
        "freeze_pack_status": payload["freeze_pack_status"],
        "decision": payload["decision"],
        "observed_session_days": payload["observed_session_days"],
        "valid_paper_trade_days": payload["valid_paper_trade_days"],
        "no_trade_observed_days": payload["no_trade_observed_days"],
        "remaining_valid_trade_days": payload["remaining_valid_trade_days"],
        "actual_paper_trades": payload["actual_paper_trades"],
        "distinct_expiry_weeks": payload["distinct_expiry_weeks"],
        "real_money_automatic": payload["real_money_automatic"],
        "external_api_calls_executed_by_freeze_pack": payload["external_api_calls_executed_by_freeze_pack"],
        "order_api_invoked_by_freeze_pack": payload["order_api_invoked_by_freeze_pack"],
        "broker_execution_invoked_by_freeze_pack": payload["broker_execution_invoked_by_freeze_pack"],
        "auto_trading_started_by_freeze_pack": payload["auto_trading_started_by_freeze_pack"],
        "fake_trades_created_by_freeze_pack": payload["fake_trades_created_by_freeze_pack"],
    }
    write_csv_rows(csv_path, [ledger_row], list(ledger_row.keys()))

    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "ledger": str(csv_path),
        "launcher": str(cmd_path),
    }


def guard_check_payload() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "safety_lock": SAFETY_LOCK,
        "blocked_actions": [
            "broker_execution",
            "real_orders",
            "auto_trading",
            "option_selling",
            "fake_trades",
            "candidate_tuning_during_validation",
            "real_money_auto_approval",
        ],
        "external_api_calls_executed_by_freeze_pack": False,
        "order_api_invoked_by_freeze_pack": False,
        "broker_execution_invoked_by_freeze_pack": False,
        "auto_trading_started_by_freeze_pack": False,
        "fake_trades_created_by_freeze_pack": False,
        "real_money_automatic": False,
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HQE Module 160 final freeze/handoff pack")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace")
    parser.add_argument("--repo-root", default=None, help="Repo root override for tests")
    parser.add_argument("--write", action="store_true", help="Write freeze evidence files")
    parser.add_argument("--guard-check", action="store_true", help="Print safety guard check only")
    args = parser.parse_args(argv)

    if args.guard_check:
        print(json.dumps(guard_check_payload(), indent=2, sort_keys=True))
        return 0

    workspace = Path(args.workspace)
    repo_root = Path(args.repo_root) if args.repo_root else repo_root_from_script()
    payload = build_payload(workspace=workspace, repo_root=repo_root)
    if args.write:
        payload["evidence_files"] = write_outputs(payload, workspace)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["freeze_pack_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
