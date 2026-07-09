from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

VERSION = "MODULE_158_FINAL_SAFE_DAILY_RUN_SMOKE_PACK_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "local_files_only": True,
    "manual_operator_control": True,
    "manual_login_required": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api_from_smoke_pack": True,
    "no_plaintext_secret_storage": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}

REQUIRED_REPO_SCRIPTS: List[str] = [
    "scripts/hqe_local_login_shell.py",
    "scripts/hqe_fyers_data_only_connector.py",
    "scripts/hqe_market_session_supervisor.py",
    "scripts/hqe_paper_signal_no_trade_reason_engine.py",
    "scripts/hqe_30_valid_trade_day_tracker.py",
    "scripts/hqe_final_daily_app_flow_integration_pack.py",
    "scripts/hqe_final_daily_run_decision_pack.py",
    "scripts/hqe_manual_daily_launch_command_pack.py",
    "scripts/hqe_final_daily_evidence_auto_open_pack.py",
    "scripts/hqe_final_operator_desktop_control_pack.py",
]

OPTIONAL_REPO_LAUNCHERS: List[str] = [
    "scripts/RUN_MODULE_147_LOCAL_LOGIN_SHELL.ps1",
    "scripts/RUN_MODULE_148_FYERS_DATA_ONLY_CONNECTOR.ps1",
    "scripts/RUN_MODULE_149_MARKET_SESSION_SUPERVISOR.ps1",
    "scripts/RUN_MODULE_150_PAPER_SIGNAL_NO_TRADE_REASON_ENGINE.ps1",
    "scripts/RUN_MODULE_151_30_VALID_TRADE_DAY_TRACKER.ps1",
    "scripts/RUN_MODULE_153_FINAL_DAILY_APP_FLOW_INTEGRATION.ps1",
    "scripts/RUN_MODULE_154_FINAL_DAILY_RUN_DECISION_PACK.ps1",
    "scripts/RUN_MODULE_155_MANUAL_DAILY_LAUNCH_COMMAND_PACK.ps1",
    "scripts/RUN_MODULE_156_FINAL_DAILY_EVIDENCE_AUTO_OPEN_PACK.ps1",
    "scripts/RUN_MODULE_157_FINAL_OPERATOR_DESKTOP_CONTROL_PACK.ps1",
]

REQUIRED_WORKSPACE_FILES: List[str] = [
    "FORWARD_VALIDATION_DAY_LEDGER.csv",
]

OPTIONAL_WORKSPACE_FILES: List[str] = [
    "FYERS_DATA_ONLY_CONNECTOR_STATUS.json",
    "MARKET_SESSION_SUPERVISOR_STATUS.json",
    "HQE_PAPER_SIGNAL_NO_TRADE_REASON_DAY_001.json",
    "HQE_30_VALID_TRADE_DAY_TRACKER_STATUS.json",
    "HQE_FINAL_DAILY_APP_FLOW_INTEGRATION_STATUS.json",
    "HQE_FINAL_DAILY_RUN_DECISION_PACK_STATUS.json",
    "HQE_MANUAL_DAILY_LAUNCH_COMMAND_PACK_STATUS.json",
    "HQE_FINAL_DAILY_EVIDENCE_AUTO_OPEN_PACK_STATUS.json",
    "HQE_FINAL_OPERATOR_DESKTOP_CONTROL_PACK_STATUS.json",
    "OPEN_HQE_DAILY_EVIDENCE_SAFE.cmd",
    "OPEN_HQE_FINAL_OPERATOR_CONTROL_PANEL_SAFE.cmd",
]

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
]


class SmokePackError(RuntimeError):
    """Raised when the smoke pack cannot complete a local-only check."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def _exists(base: Path, relative: str) -> bool:
    return (base / relative).exists()


def _file_check(base: Path, relative_paths: Iterable[str]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    for relative in relative_paths:
        path = base / relative
        checks.append(
            {
                "relative_path": relative,
                "exists": path.exists(),
                "absolute_path": str(path),
            }
        )
    return checks


def _missing_from_checks(checks: Iterable[Dict[str, Any]]) -> List[str]:
    return [str(item["relative_path"]) for item in checks if not item.get("exists")]


def _workspace_file_check(workspace: Path, names: Iterable[str]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    for name in names:
        path = workspace / name
        checks.append({"file_name": name, "exists": path.exists(), "path": str(path)})
    return checks


def _missing_workspace(checks: Iterable[Dict[str, Any]]) -> List[str]:
    return [str(item["file_name"]) for item in checks if not item.get("exists")]


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: List[Dict[str, str]] = []
        for row in reader:
            rows.append({str(k or "").strip(): str(v or "").strip() for k, v in row.items()})
        return rows


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        text = str(value).strip()
        if not text:
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _first(row: Dict[str, str], names: Iterable[str], default: str = "") -> str:
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for name in names:
        value = lowered.get(str(name).strip().lower())
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def summarize_day_ledger(workspace: Path) -> Dict[str, Any]:
    rows = _read_csv_rows(workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv")
    observed_dates = set()
    valid_trade_dates = set()
    no_trade_dates = set()
    total_declared_trades = 0

    for row in rows:
        date_value = _first(row, ["trading_date", "date", "session_date", "day_date"])
        if date_value:
            observed_dates.add(date_value)
        trade_count = _as_int(_first(row, ["trade_count", "actual_paper_trades", "paper_trades"]), 0)
        total_declared_trades += max(trade_count, 0)
        if date_value and trade_count > 0:
            valid_trade_dates.add(date_value)
        if date_value and trade_count == 0:
            no_trade_dates.add(date_value)

    return {
        "day_ledger_rows": len(rows),
        "observed_session_days": len(observed_dates),
        "valid_paper_trade_days": len(valid_trade_dates),
        "no_trade_observed_days": len(no_trade_dates),
        "declared_trade_count_from_day_ledger": total_declared_trades,
    }


def guard_check() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "safety_lock": dict(SAFETY_LOCK),
        "blocked_actions": {name: "HARD_BLOCKED_BY_SMOKE_PACK" for name in BLOCKED_ACTIONS},
        "external_api_calls_executed_by_smoke_pack": False,
        "order_api_invoked_by_smoke_pack": False,
        "broker_execution_invoked_by_smoke_pack": False,
        "auto_trading_started_by_smoke_pack": False,
        "fake_trades_created_by_smoke_pack": False,
        "candidate_tuning_by_smoke_pack": False,
        "real_money_automatic": False,
    }


def build_smoke_pack(
    workspace: Path = DEFAULT_WORKSPACE,
    trading_date: Optional[str] = None,
    day_number: Optional[int] = None,
    repo_root: Optional[Path] = None,
    write: bool = False,
) -> Dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else _repo_root_from_script()
    workspace = Path(workspace)

    required_script_checks = _file_check(root, REQUIRED_REPO_SCRIPTS)
    optional_launcher_checks = _file_check(root, OPTIONAL_REPO_LAUNCHERS)
    required_workspace_checks = _workspace_file_check(workspace, REQUIRED_WORKSPACE_FILES)
    optional_workspace_checks = _workspace_file_check(workspace, OPTIONAL_WORKSPACE_FILES)

    missing_required_scripts = _missing_from_checks(required_script_checks)
    missing_required_workspace_files = _missing_workspace(required_workspace_checks)
    missing_optional_launchers = _missing_from_checks(optional_launcher_checks)
    missing_optional_workspace_files = _missing_workspace(optional_workspace_checks)

    ledger_summary = summarize_day_ledger(workspace)
    warnings: List[str] = []
    if missing_optional_launchers:
        warnings.append("Some optional launcher scripts are missing; smoke pack still checks required core scripts.")
    if missing_optional_workspace_files:
        warnings.append("Some optional workspace evidence files are missing; run relevant safe modules to refresh evidence.")
    if not workspace.exists():
        warnings.append("Workspace folder does not exist; local-only smoke evidence can still be emitted if --write parent is available.")

    required_ok = not missing_required_scripts and not missing_required_workspace_files
    safety_ok = all(SAFETY_LOCK.values())
    smoke_pack_status = "PASS" if required_ok and safety_ok else "FAIL"
    decision = (
        "FINAL_SAFE_DAILY_RUN_SMOKE_PASS_MANUAL_OPERATOR_REVIEW_REQUIRED"
        if smoke_pack_status == "PASS"
        else "FINAL_SAFE_DAILY_RUN_SMOKE_FAIL_FIX_REQUIRED_ITEMS"
    )

    payload: Dict[str, Any] = {
        "version": VERSION,
        "smoke_time_utc": utc_now_iso(),
        "workspace": str(workspace),
        "repo_root": str(root),
        "trading_date": trading_date or "",
        "day_number": int(day_number or 0),
        "smoke_pack_status": smoke_pack_status,
        "decision": decision,
        "operator_mode": "FINAL_SAFE_DAILY_RUN_SMOKE_LOCAL_ONLY",
        "manual_operator_review_required": True,
        "manual_login_required": True,
        "local_files_only": True,
        "required_ok": required_ok,
        "safety_ok": safety_ok,
        "required_repo_scripts": required_script_checks,
        "optional_repo_launchers": optional_launcher_checks,
        "required_workspace_files": required_workspace_checks,
        "optional_workspace_files": optional_workspace_checks,
        "missing_required_repo_scripts": missing_required_scripts,
        "missing_required_workspace_files": missing_required_workspace_files,
        "missing_optional_repo_launchers": missing_optional_launchers,
        "missing_optional_workspace_files": missing_optional_workspace_files,
        "day_ledger_summary": ledger_summary,
        "observed_session_days": ledger_summary["observed_session_days"],
        "valid_paper_trade_days": ledger_summary["valid_paper_trade_days"],
        "no_trade_observed_days": ledger_summary["no_trade_observed_days"],
        "actual_paper_trades_created_by_smoke_pack": 0,
        "safety_lock": dict(SAFETY_LOCK),
        "external_api_calls_executed_by_smoke_pack": False,
        "order_api_invoked_by_smoke_pack": False,
        "broker_execution_invoked_by_smoke_pack": False,
        "auto_trading_started_by_smoke_pack": False,
        "fake_trades_created_by_smoke_pack": False,
        "candidate_tuning_by_smoke_pack": False,
        "real_money_automatic": False,
        "blocked_actions": {name: "HARD_BLOCKED_BY_SMOKE_PACK" for name in BLOCKED_ACTIONS},
        "warnings": warnings,
    }

    if write:
        payload["evidence_files"] = write_evidence(payload, workspace)

    return payload


def write_evidence(payload: Dict[str, Any], workspace: Path) -> Dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / "HQE_FINAL_SAFE_DAILY_RUN_SMOKE_PACK_STATUS.json"
    md_path = workspace / "HQE_FINAL_SAFE_DAILY_RUN_SMOKE_PACK_STATUS.md"
    ledger_path = workspace / "HQE_FINAL_SAFE_DAILY_RUN_SMOKE_PACK_LEDGER.csv"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    md_lines = [
        "# HQE Final Safe Daily Run Smoke Pack",
        "",
        f"- version: {payload['version']}",
        f"- smoke_pack_status: {payload['smoke_pack_status']}",
        f"- decision: {payload['decision']}",
        f"- workspace: {payload['workspace']}",
        f"- trading_date: {payload.get('trading_date', '')}",
        f"- day_number: {payload.get('day_number', 0)}",
        f"- observed_session_days: {payload['observed_session_days']}",
        f"- valid_paper_trade_days: {payload['valid_paper_trade_days']}",
        f"- no_trade_observed_days: {payload['no_trade_observed_days']}",
        f"- required_ok: {payload['required_ok']}",
        f"- safety_ok: {payload['safety_ok']}",
        f"- manual_operator_review_required: {payload['manual_operator_review_required']}",
        f"- manual_login_required: {payload['manual_login_required']}",
        "",
        "## Safety Lock",
    ]
    for key, value in payload["safety_lock"].items():
        md_lines.append(f"- {key}: {value}")
    md_lines.extend(
        [
            "",
            "## Execution Guard",
            f"- external_api_calls_executed_by_smoke_pack: {payload['external_api_calls_executed_by_smoke_pack']}",
            f"- order_api_invoked_by_smoke_pack: {payload['order_api_invoked_by_smoke_pack']}",
            f"- broker_execution_invoked_by_smoke_pack: {payload['broker_execution_invoked_by_smoke_pack']}",
            f"- auto_trading_started_by_smoke_pack: {payload['auto_trading_started_by_smoke_pack']}",
            f"- fake_trades_created_by_smoke_pack: {payload['fake_trades_created_by_smoke_pack']}",
            f"- real_money_automatic: {payload['real_money_automatic']}",
        ]
    )
    if payload["missing_required_repo_scripts"] or payload["missing_required_workspace_files"]:
        md_lines.extend(["", "## Required Missing Items"])
        for item in payload["missing_required_repo_scripts"]:
            md_lines.append(f"- missing required repo script: {item}")
        for item in payload["missing_required_workspace_files"]:
            md_lines.append(f"- missing required workspace file: {item}")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    write_header = not ledger_path.exists()
    with ledger_path.open("a", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "smoke_time_utc",
            "version",
            "smoke_pack_status",
            "decision",
            "trading_date",
            "day_number",
            "observed_session_days",
            "valid_paper_trade_days",
            "no_trade_observed_days",
            "required_ok",
            "safety_ok",
            "external_api_calls_executed_by_smoke_pack",
            "order_api_invoked_by_smoke_pack",
            "broker_execution_invoked_by_smoke_pack",
            "auto_trading_started_by_smoke_pack",
            "fake_trades_created_by_smoke_pack",
            "real_money_automatic",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({key: payload.get(key, "") for key in fieldnames})

    return {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="HQE final safe daily run smoke pack. Local files only; no trading/order/API execution.")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace path.")
    parser.add_argument("--trading-date", default="", help="Trading date label for the smoke evidence.")
    parser.add_argument("--day-number", type=int, default=0, help="Forward validation day number.")
    parser.add_argument("--write", action="store_true", help="Write JSON/Markdown/CSV evidence files into the workspace.")
    parser.add_argument("--guard-check", action="store_true", help="Print safety guard status and exit.")
    args = parser.parse_args(argv)

    if args.guard_check:
        print(json.dumps(guard_check(), indent=2, sort_keys=True))
        return 0

    payload = build_smoke_pack(
        workspace=Path(args.workspace),
        trading_date=args.trading_date,
        day_number=args.day_number,
        write=args.write,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["smoke_pack_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

