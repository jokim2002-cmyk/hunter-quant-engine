#!/usr/bin/env python3
"""HQE Module 159: 30-Day Paper Validation Daily Operating SOP.

Purpose
-------
Create a local-only daily operating SOP for the forward paper validation phase.

Safety lock
-----------
- Paper/simulation only.
- No real money.
- No broker execution.
- No real orders.
- No auto trading.
- No option selling.
- No external API calls from this SOP tool.
- No fake trades.
- No candidate tuning during validation.
- No profitability claim.

Important rule
--------------
Observed session days and valid paper trade days are different counters:
- Observed session day: HQE ran / market watched / report generated.
- Valid paper trade day: day with at least one actual paper trade row.
- No-trade days are observed days, but do not count toward the 30 valid trade-day target.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

VERSION = "MODULE_159_30_DAY_PAPER_VALIDATION_DAILY_OPERATING_SOP_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
TARGET_VALID_TRADE_DAYS = 30

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api_from_sop": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
    "real_money_manual_review_required": True,
}

EXECUTION_GUARDS: Dict[str, bool] = {
    "external_api_calls_executed_by_sop": False,
    "order_api_invoked_by_sop": False,
    "broker_execution_invoked_by_sop": False,
    "auto_trading_started_by_sop": False,
    "fake_trades_created_by_sop": False,
    "candidate_tuning_performed_by_sop": False,
    "real_money_automatic": False,
}

SOP_DAILY_STEPS: List[str] = [
    "PC ON, open HQE local login/startup gate.",
    "Login manually with local HQE credential gate.",
    "Open final operator control panel / manual daily launch pack.",
    "Run final daily run decision pack before market or at operator start time.",
    "Run/monitor market session supervisor for 09:15 to 15:30 IST watch window.",
    "Run Fyers data-only preflight when live-data module is manually configured; order APIs remain hard-blocked.",
    "Run paper signal + no-trade reason engine using real paper signal evidence only.",
    "Record day close after market: trade_count must come from actual paper trade rows, not fake rows.",
    "Update 30 valid trade-day tracker: no-trade days count as observed sessions only.",
    "Open daily evidence shortcut/control pack and review JSON/MD/CSV outputs.",
]

SOP_RULES: Dict[str, bool] = {
    "observed_session_day_requires_hqe_run_market_watch_report": True,
    "no_trade_day_counts_as_observed_session_day": True,
    "no_trade_day_counts_as_valid_trade_day": False,
    "valid_trade_day_requires_at_least_one_actual_paper_trade": True,
    "actual_trade_rows_required_for_trade_count": True,
    "expiry_weeks_based_only_on_actual_trade_rows": True,
    "fake_trades_allowed": False,
    "candidate_tuning_during_validation_allowed": False,
    "real_money_allowed_automatically_after_30_days": False,
    "manual_review_required_after_30_valid_trade_days": True,
}

REQUIRED_SAFE_SCRIPT_HINTS: List[str] = [
    "scripts/hqe_local_login_shell.py",
    "scripts/hqe_fyers_data_only_connector.py",
    "scripts/hqe_market_session_supervisor.py",
    "scripts/hqe_paper_signal_no_trade_reason_engine.py",
    "scripts/evaluate_forward_validation_day_ledger.py",
    "scripts/hqe_30_valid_trade_day_tracker.py",
    "scripts/hqe_final_daily_app_flow_integration_pack.py",
    "scripts/hqe_final_daily_run_decision_pack.py",
    "scripts/hqe_manual_daily_launch_command_pack.py",
    "scripts/hqe_final_daily_evidence_auto_open_pack.py",
    "scripts/hqe_final_operator_desktop_control_pack.py",
    "scripts/hqe_final_safe_daily_run_smoke_pack.py",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_header_name(value: str) -> str:
    return str(value or "").replace("\ufeff", "").strip().lower()


def _normalize_row(row: Mapping[str, Any]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in row.items():
        normalized[_normalize_header_name(str(key))] = "" if value is None else str(value).strip()
    return normalized


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [_normalize_row(row) for row in reader]


def _first_present(row: Mapping[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = row.get(_normalize_header_name(name), "")
        if str(value).strip():
            return str(value).strip()
    return ""


def _parse_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        text = str(value).strip()
        if not text:
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _day_key(row: Mapping[str, str]) -> str:
    return _first_present(row, ["trading_date", "date", "day_date", "session_date"])


def _trade_count(row: Mapping[str, str]) -> int:
    return _parse_int(_first_present(row, ["trade_count", "actual_paper_trades", "paper_trade_count", "trades"]), 0)


def count_day_ledger(workspace: Path) -> Dict[str, Any]:
    day_ledger_path = workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv"
    rows = _read_csv_rows(day_ledger_path)

    observed_days: Set[str] = set()
    valid_trade_days: Set[str] = set()
    day_details: List[Dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        day = _day_key(row) or f"UNKNOWN_ROW_{index}"
        count = _trade_count(row)
        observed_days.add(day)
        if count > 0:
            valid_trade_days.add(day)
        day_details.append(
            {
                "row_number": index,
                "trading_date": day,
                "trade_count": count,
                "counts_as_observed_session_day": True,
                "counts_as_valid_paper_trade_day": count > 0,
            }
        )

    observed_count = len(observed_days)
    valid_count = len(valid_trade_days)
    no_trade_count = max(0, observed_count - valid_count)

    return {
        "day_ledger_path": str(day_ledger_path),
        "day_ledger_exists": day_ledger_path.exists(),
        "day_ledger_rows": len(rows),
        "observed_session_days": observed_count,
        "valid_paper_trade_days": valid_count,
        "no_trade_observed_days": no_trade_count,
        "remaining_valid_trade_days": max(0, TARGET_VALID_TRADE_DAYS - valid_count),
        "target_valid_trade_days": TARGET_VALID_TRADE_DAYS,
        "day_details": day_details,
    }


def _script_presence(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    root = repo_root or Path.cwd()
    scripts: Dict[str, bool] = {}
    for rel in REQUIRED_SAFE_SCRIPT_HINTS:
        scripts[rel] = (root / rel).exists()
    missing = [rel for rel, exists in scripts.items() if not exists]
    return {
        "repo_root": str(root),
        "required_safe_scripts": scripts,
        "missing_required_safe_scripts": missing,
        "all_required_safe_scripts_present": not missing,
    }


def build_sop_payload(
    workspace: Path,
    trading_date: str = "",
    day_number: Optional[int] = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    workspace = Path(workspace)
    counts = count_day_ledger(workspace)
    scripts = _script_presence(repo_root)

    warnings: List[str] = []
    if not counts["day_ledger_exists"]:
        warnings.append("FORWARD_VALIDATION_DAY_LEDGER.csv not found; counters default to zero until day close evidence exists.")
    if scripts["missing_required_safe_scripts"]:
        warnings.append("Some safe-flow scripts were not found from current repo root; run from repo root for full script presence check.")

    payload: Dict[str, Any] = {
        "version": VERSION,
        "generated_at_utc": _utc_now_iso(),
        "workspace": str(workspace),
        "trading_date": trading_date,
        "day_number": day_number,
        "sop_status": "PASS",
        "operator_mode": "30_DAY_PAPER_VALIDATION_DAILY_OPERATING_SOP_LOCAL_ONLY",
        "decision": "30_DAY_PAPER_VALIDATION_SOP_READY_MANUAL_OPERATOR_REQUIRED",
        "target_valid_trade_days": TARGET_VALID_TRADE_DAYS,
        "observed_session_days": counts["observed_session_days"],
        "valid_paper_trade_days": counts["valid_paper_trade_days"],
        "no_trade_observed_days": counts["no_trade_observed_days"],
        "remaining_valid_trade_days": counts["remaining_valid_trade_days"],
        "daily_operating_rules": SOP_RULES,
        "daily_operating_steps": SOP_DAILY_STEPS,
        "safety_lock": SAFETY_LOCK,
        "execution_guards": EXECUTION_GUARDS,
        "real_money_policy": {
            "real_money_now": False,
            "real_money_automatic_after_target": False,
            "manual_review_required_after_30_valid_trade_days": True,
            "future_explicit_user_approval_required": True,
            "profitability_claim_made_by_sop": False,
        },
        "counter_policy": {
            "observed_session_days_count_no_trade_days": True,
            "valid_paper_trade_days_count_only_days_with_actual_trade_count_gt_zero": True,
            "actual_paper_trade_count_must_come_from_trade_ledgers_only": True,
            "expiry_weeks_must_come_from_actual_trade_rows_only": True,
        },
        "day_ledger_summary": counts,
        "script_presence": scripts,
        "manual_operator_review_required": True,
        "manual_login_required": True,
        "warnings": warnings,
    }
    payload.update(EXECUTION_GUARDS)
    return payload


def _markdown_from_payload(payload: Mapping[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# HQE 30-Day Paper Validation Daily Operating SOP")
    lines.append("")
    lines.append(f"- Version: `{payload['version']}`")
    lines.append(f"- SOP status: **{payload['sop_status']}**")
    lines.append(f"- Decision: **{payload['decision']}**")
    lines.append(f"- Workspace: `{payload['workspace']}`")
    lines.append(f"- Trading date: `{payload.get('trading_date') or 'not specified'}`")
    lines.append(f"- Day number: `{payload.get('day_number') if payload.get('day_number') is not None else 'not specified'}`")
    lines.append("")
    lines.append("## Current Counters")
    lines.append("")
    lines.append(f"- Observed session days: **{payload['observed_session_days']}**")
    lines.append(f"- Valid paper trade days: **{payload['valid_paper_trade_days']}**")
    lines.append(f"- No-trade observed days: **{payload['no_trade_observed_days']}**")
    lines.append(f"- Remaining valid trade days: **{payload['remaining_valid_trade_days']}**")
    lines.append(f"- Target valid trade days: **{payload['target_valid_trade_days']}**")
    lines.append("")
    lines.append("## Daily Operating Steps")
    lines.append("")
    for index, step in enumerate(payload["daily_operating_steps"], start=1):
        lines.append(f"{index}. {step}")
    lines.append("")
    lines.append("## Counter Rules")
    lines.append("")
    lines.append("- No-trade days count as observed session days only.")
    lines.append("- Valid paper trade day requires at least one actual paper trade.")
    lines.append("- Fake trades are not allowed.")
    lines.append("- Candidate tuning during validation is not allowed.")
    lines.append("- Real money is not automatic after 30 valid paper trade days; manual review and future explicit approval are required.")
    lines.append("")
    lines.append("## Safety Lock")
    lines.append("")
    for key, value in payload["safety_lock"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.append("")
    lines.append("## Execution Guards")
    lines.append("")
    for key, value in payload["execution_guards"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.append("")
    if payload.get("warnings"):
        lines.append("## Warnings")
        lines.append("")
        for warning in payload["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _cmd_launcher_text(json_path: Path, md_path: Path) -> str:
    return "\n".join(
        [
            "@echo off",
            "setlocal",
            "title HQE 30-Day Paper Validation SOP - SAFE LOCAL ONLY",
            "echo HQE 30-Day Paper Validation SOP",
            "echo.",
            "echo SAFETY: local evidence/SOP only. No broker, no orders, no auto trading, no real money.",
            "echo.",
            f"echo JSON: {json_path}",
            f"echo MD  : {md_path}",
            "echo.",
            f"if exist \"{md_path}\" start \"\" \"{md_path}\"",
            "pause",
            "endlocal",
            "",
        ]
    )


def write_sop_outputs(workspace: Path, payload: Mapping[str, Any]) -> Dict[str, str]:
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    json_path = workspace / "HQE_30_DAY_PAPER_VALIDATION_DAILY_OPERATING_SOP.json"
    md_path = workspace / "HQE_30_DAY_PAPER_VALIDATION_DAILY_OPERATING_SOP.md"
    cmd_path = workspace / "OPEN_HQE_30_DAY_PAPER_VALIDATION_SOP_SAFE.cmd"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_markdown_from_payload(payload), encoding="utf-8")
    cmd_path.write_text(_cmd_launcher_text(json_path, md_path), encoding="utf-8")

    return {"json": str(json_path), "markdown": str(md_path), "cmd": str(cmd_path)}


def guard_check_payload() -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "version": VERSION,
        "guard_check_status": "PASS",
        "operator_mode": "30_DAY_PAPER_VALIDATION_DAILY_OPERATING_SOP_LOCAL_ONLY",
        "safety_lock": SAFETY_LOCK,
        "execution_guards": EXECUTION_GUARDS,
        "daily_operating_rules": SOP_RULES,
    }
    payload.update(EXECUTION_GUARDS)
    return payload


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQE 30-Day Paper Validation Daily Operating SOP")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace folder")
    parser.add_argument("--trading-date", default="", help="Trading date for SOP context, YYYY-MM-DD")
    parser.add_argument("--day-number", type=int, default=None, help="Forward validation day number")
    parser.add_argument("--write", action="store_true", help="Write JSON/MD/CMD evidence files to workspace")
    parser.add_argument("--guard-check", action="store_true", help="Print safety guard check only")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    if args.guard_check:
        print(json.dumps(guard_check_payload(), indent=2, sort_keys=True))
        return 0

    workspace = Path(args.workspace)
    payload = build_sop_payload(workspace=workspace, trading_date=args.trading_date, day_number=args.day_number)
    if args.write:
        payload["evidence_files"] = write_sop_outputs(workspace, payload)
        json_path = workspace / "HQE_30_DAY_PAPER_VALIDATION_DAILY_OPERATING_SOP.json"
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
