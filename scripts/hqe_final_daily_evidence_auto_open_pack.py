from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "MODULE_156_FINAL_DAILY_EVIDENCE_AUTO_OPEN_PACK_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_TRADING_DATE = "2026-07-09"
DEFAULT_DAY_NUMBER = 1

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "local_files_only": True,
    "manual_operator_open_required": True,
    "no_auto_trading": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_real_money": True,
    "no_option_selling": True,
    "no_external_api": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}

# These are local evidence/report files created by earlier safe modules.
# Missing files do not fail the pack; they are reported clearly for the operator.
EVIDENCE_PATTERNS = [
    ("day_close_json", "DAY_{day:03d}_FORWARD_VALIDATION_DAY_CLOSE.json"),
    ("day_close_markdown", "DAY_{day:03d}_FORWARD_VALIDATION_DAY_CLOSE.md"),
    ("day_ledger_csv", "FORWARD_VALIDATION_DAY_LEDGER.csv"),
    ("day_ledger_evaluation_json", "FORWARD_VALIDATION_DAY_LEDGER_EVALUATION.json"),
    ("day_ledger_evaluation_markdown", "FORWARD_VALIDATION_DAY_LEDGER_EVALUATION.md"),
    ("fyers_data_only_status_json", "FYERS_DATA_ONLY_CONNECTOR_STATUS.json"),
    ("fyers_data_only_status_markdown", "FYERS_DATA_ONLY_CONNECTOR_STATUS.md"),
    ("fyers_data_only_ledger", "FYERS_DATA_ONLY_CONNECTOR_LEDGER.csv"),
    ("market_session_supervisor_json", "HQE_MARKET_SESSION_SUPERVISOR_STATUS.json"),
    ("market_session_supervisor_markdown", "HQE_MARKET_SESSION_SUPERVISOR_STATUS.md"),
    ("paper_signal_no_trade_json", "DAY_{day:03d}_PAPER_SIGNAL_NO_TRADE_REASON.json"),
    ("paper_signal_no_trade_markdown", "DAY_{day:03d}_PAPER_SIGNAL_NO_TRADE_REASON.md"),
    ("valid_trade_day_tracker_json", "HQE_30_VALID_TRADE_DAY_TRACKER_STATUS.json"),
    ("valid_trade_day_tracker_markdown", "HQE_30_VALID_TRADE_DAY_TRACKER_STATUS.md"),
    ("final_daily_app_flow_json", "HQE_FINAL_DAILY_APP_FLOW_INTEGRATION_STATUS.json"),
    ("final_daily_app_flow_markdown", "HQE_FINAL_DAILY_APP_FLOW_INTEGRATION_STATUS.md"),
    ("final_daily_run_decision_json", "HQE_FINAL_DAILY_RUN_DECISION_PACK_STATUS.json"),
    ("final_daily_run_decision_markdown", "HQE_FINAL_DAILY_RUN_DECISION_PACK_STATUS.md"),
    ("manual_daily_launch_json", "HQE_MANUAL_DAILY_LAUNCH_COMMAND_PACK_STATUS.json"),
    ("manual_daily_launch_markdown", "HQE_MANUAL_DAILY_LAUNCH_COMMAND_PACK_STATUS.md"),
    ("daily_report_pack_json", "DAY_{day:03d}_DAILY_PAPER_TRADING_REPORT_PACK.json"),
    ("daily_report_pack_markdown", "DAY_{day:03d}_DAILY_PAPER_TRADING_REPORT_PACK.md"),
    ("dashboard_index_html", "dashboard_index.html"),
    ("operator_evidence_index_html", "operator_evidence_index.html"),
]

OUTPUT_STATUS_JSON = "HQE_DAILY_EVIDENCE_AUTO_OPEN_STATUS.json"
OUTPUT_STATUS_MD = "HQE_DAILY_EVIDENCE_AUTO_OPEN_STATUS.md"
OUTPUT_SHORTCUT_INDEX_MD = "HQE_DAILY_EVIDENCE_OPERATOR_SHORTCUT_INDEX.md"
OUTPUT_SHORTCUT_CMD = "OPEN_HQE_DAILY_EVIDENCE_SAFE.cmd"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _validate_day_number(day_number: int) -> int:
    try:
        day = int(day_number)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("day_number must be an integer") from exc
    if day < 1 or day > 999:
        raise ValueError("day_number must be between 1 and 999")
    return day


def _validate_trading_date(trading_date: str) -> str:
    try:
        datetime.strptime(trading_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("trading_date must be YYYY-MM-DD") from exc
    return trading_date


def _file_kind(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"json", "csv", "md", "html", "cmd", "txt"}:
        return suffix
    return suffix or "file"


def build_evidence_candidates(workspace: Path, trading_date: str, day_number: int) -> list[dict[str, Any]]:
    day = _validate_day_number(day_number)
    _validate_trading_date(trading_date)
    workspace = Path(workspace)
    candidates: list[dict[str, Any]] = []
    for label, pattern in EVIDENCE_PATTERNS:
        filename = pattern.format(day=day, trading_date=trading_date)
        path = workspace / filename
        candidates.append(
            {
                "label": label,
                "filename": filename,
                "path": str(path),
                "exists": path.exists(),
                "kind": _file_kind(path),
                "local_only": True,
            }
        )
    return candidates


def _build_shortcut_cmd(workspace: Path, payload: dict[str, Any]) -> str:
    present = [item for item in payload["evidence_files"] if item["exists"]]
    lines = [
        "@echo off",
        "setlocal",
        "title HQE Daily Evidence Safe Opener",
        "echo HQE Daily Evidence Safe Opener",
        "echo Paper-only evidence review. No trading. No broker execution. No order API.",
        "echo Workspace: " + str(workspace),
        "echo.",
    ]
    if not present:
        lines.append("echo No expected evidence files were found yet.")
    else:
        lines.append("echo Opening local evidence files only...")
        for item in present:
            lines.append(f'if exist "{item["path"]}" start "" "{item["path"]}"')
    lines += [
        "echo.",
        "echo Done. This launcher did not place trades, connect to broker, or call external APIs.",
        "pause",
        "endlocal",
    ]
    return "\r\n".join(lines) + "\r\n"


def _build_status_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# HQE Daily Evidence Auto-Open / Operator Shortcut Pack",
        "",
        f"- Version: `{payload['version']}`",
        f"- Status: `{payload['shortcut_pack_status']}`",
        f"- Decision: `{payload['decision']}`",
        f"- Trading date: `{payload['trading_date']}`",
        f"- Day number: `{payload['day_number']}`",
        f"- Present evidence files: `{payload['present_evidence_files_count']}`",
        f"- Missing expected files: `{payload['missing_expected_files_count']}`",
        "",
        "## Safety Lock",
        "",
    ]
    for key, value in payload["safety_lock"].items():
        lines.append(f"- {key}: `{value}`")
    lines += [
        "",
        "## Operator Shortcuts",
        "",
    ]
    for key, value in payload["operator_shortcuts"].items():
        lines.append(f"- {key}: `{value}`")
    lines += [
        "",
        "## Evidence Files",
        "",
        "| Label | Exists | File |",
        "|---|---:|---|",
    ]
    for item in payload["evidence_files"]:
        lines.append(f"| {item['label']} | {item['exists']} | `{item['filename']}` |")
    lines.append("")
    lines.append("This pack is local evidence review only. It does not execute trades, broker actions, order APIs, or external API calls.")
    lines.append("")
    return "\n".join(lines)


def _build_shortcut_index_markdown(payload: dict[str, Any]) -> str:
    present = [item for item in payload["evidence_files"] if item["exists"]]
    missing = [item for item in payload["evidence_files"] if not item["exists"]]
    lines = [
        "# HQE Operator Evidence Shortcut Index",
        "",
        f"Trading date: `{payload['trading_date']}`  ",
        f"Day number: `{payload['day_number']}`  ",
        "",
        "## Present Local Evidence",
        "",
    ]
    if present:
        for item in present:
            lines.append(f"- **{item['label']}** — `{item['path']}`")
    else:
        lines.append("- No expected evidence files are present yet.")
    lines += ["", "## Missing Expected Evidence", ""]
    if missing:
        for item in missing:
            lines.append(f"- **{item['label']}** — `{item['filename']}`")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Safety",
        "",
        "Paper-only evidence review. No broker execution. No real orders. No auto trading. No option selling. No external API calls.",
        "",
    ]
    return "\n".join(lines)


def build_shortcut_pack(
    workspace: Path,
    trading_date: str = DEFAULT_TRADING_DATE,
    day_number: int = DEFAULT_DAY_NUMBER,
    write: bool = False,
) -> dict[str, Any]:
    workspace = Path(workspace)
    day = _validate_day_number(day_number)
    trading_date = _validate_trading_date(trading_date)

    if write:
        workspace.mkdir(parents=True, exist_ok=True)

    evidence_files = build_evidence_candidates(workspace, trading_date, day)
    present_count = sum(1 for item in evidence_files if item["exists"])
    missing_count = len(evidence_files) - present_count

    status_json = workspace / OUTPUT_STATUS_JSON
    status_md = workspace / OUTPUT_STATUS_MD
    shortcut_index_md = workspace / OUTPUT_SHORTCUT_INDEX_MD
    shortcut_cmd = workspace / OUTPUT_SHORTCUT_CMD

    payload: dict[str, Any] = {
        "version": VERSION,
        "shortcut_pack_status": "PASS",
        "decision": "DAILY_EVIDENCE_SHORTCUT_PACK_READY_LOCAL_FILES_ONLY",
        "workspace": str(workspace),
        "trading_date": trading_date,
        "day_number": day,
        "created_at_utc": _now_utc(),
        "evidence_files": evidence_files,
        "present_evidence_files_count": present_count,
        "missing_expected_files_count": missing_count,
        "operator_shortcuts": {
            "status_json": str(status_json),
            "status_markdown": str(status_md),
            "shortcut_index_markdown": str(shortcut_index_md),
            "manual_safe_open_cmd": str(shortcut_cmd),
        },
        "manual_operator_open_required": True,
        "auto_open_launcher_emitted": bool(write),
        "auto_open_executed_by_pack": False,
        "local_files_only": True,
        "external_api_calls_executed_by_shortcut_pack": False,
        "order_api_invoked_by_shortcut_pack": False,
        "broker_execution_invoked_by_shortcut_pack": False,
        "auto_trading_started_by_shortcut_pack": False,
        "fake_trades_created_by_shortcut_pack": False,
        "candidate_tuning_by_shortcut_pack": False,
        "real_money_automatic": False,
        "safety_lock": dict(SAFETY_LOCK),
        "warnings": [],
    }

    if present_count == 0:
        payload["warnings"].append("No expected evidence files were found yet; run the daily workflow/evidence modules first.")

    if write:
        status_json.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
        status_md.write_text(_build_status_markdown(payload), encoding="utf-8")
        shortcut_index_md.write_text(_build_shortcut_index_markdown(payload), encoding="utf-8")
        shortcut_cmd.write_text(_build_shortcut_cmd(workspace, payload), encoding="utf-8")

    return payload


def guard_check() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "shortcut_pack_status": "PASS",
        "local_files_only": True,
        "external_api_calls_executed_by_shortcut_pack": False,
        "order_api_invoked_by_shortcut_pack": False,
        "broker_execution_invoked_by_shortcut_pack": False,
        "auto_trading_started_by_shortcut_pack": False,
        "fake_trades_created_by_shortcut_pack": False,
        "candidate_tuning_by_shortcut_pack": False,
        "real_money_automatic": False,
        "safety_lock": dict(SAFETY_LOCK),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HQE final daily evidence auto-open/operator shortcut pack")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace")
    parser.add_argument("--trading-date", default=DEFAULT_TRADING_DATE, help="Trading date YYYY-MM-DD")
    parser.add_argument("--day-number", type=int, default=DEFAULT_DAY_NUMBER, help="Forward day number")
    parser.add_argument("--write", action="store_true", help="Write status/index/manual shortcut files")
    parser.add_argument("--guard-check", action="store_true", help="Print safety guard status only")
    args = parser.parse_args(argv)

    if args.guard_check:
        payload = guard_check()
    else:
        payload = build_shortcut_pack(
            workspace=Path(args.workspace),
            trading_date=args.trading_date,
            day_number=args.day_number,
            write=args.write,
        )
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
