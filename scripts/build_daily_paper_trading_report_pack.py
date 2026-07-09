"""
Module 133: Daily Paper Trading Report Pack

Builds a deterministic daily report pack from Module 131 supervisor output
and Module 132 reason overlay output.

Safety contract:
- Paper/simulation only
- No broker execution
- No real orders
- No real money approval
- No auto trading
- No option selling
- No profitability claim
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


MODULE_ID = 133
MODULE_NAME = "Daily Paper Trading Report Pack"

PAPER_ONLY = True
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
REAL_MONEY_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False
PROFITABILITY_CLAIM = False

LOCKED_CANDIDATE = "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120"


@dataclass(frozen=True)
class ReportPackInputs:
    day_label: str
    supervisor_summary: Path | None
    supervisor_report: Path | None
    reason_log: Path | None
    paper_ledger: Path | None
    overlay_json: Path | None
    overlay_report: Path | None
    overlay_audit_csv: Path | None
    out_dir: Path


def assert_safety_contract() -> None:
    if not PAPER_ONLY:
        raise RuntimeError("SAFETY_FAIL: PAPER_ONLY must stay True.")
    blocked = {
        "BROKER_EXECUTION_ALLOWED": BROKER_EXECUTION_ALLOWED,
        "REAL_ORDERS_ALLOWED": REAL_ORDERS_ALLOWED,
        "REAL_MONEY_ALLOWED": REAL_MONEY_ALLOWED,
        "AUTO_TRADING_ALLOWED": AUTO_TRADING_ALLOWED,
        "OPTION_SELLING_ALLOWED": OPTION_SELLING_ALLOWED,
        "PROFITABILITY_CLAIM": PROFITABILITY_CLAIM,
    }
    enabled = [name for name, value in blocked.items() if value]
    if enabled:
        raise RuntimeError("SAFETY_FAIL: blocked capability enabled: " + ",".join(enabled))


def read_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def read_csv_rows(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if text == "":
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1", "y"}


def pick(*values: Any, default: Any = "") -> Any:
    for value in values:
        if value is not None and str(value).strip() != "":
            return value
    return default


def aggregate_ledger(rows: list[dict[str, str]]) -> dict[str, Any]:
    opened = [row for row in rows if str(row.get("event", "")).upper() == "POSITION_OPENED"]
    closed = [row for row in rows if str(row.get("event", "")).upper() == "POSITION_CLOSED"]
    pnl_values = [safe_float(row.get("paper_pnl")) for row in closed]
    wins = len([pnl for pnl in pnl_values if pnl > 0])
    losses = len([pnl for pnl in pnl_values if pnl < 0])
    flats = len([pnl for pnl in pnl_values if pnl == 0])
    total_pnl = round(sum(pnl_values), 2)
    avg_pnl = round(total_pnl / len(closed), 2) if closed else 0.0
    open_positions = max(0, len(opened) - len(closed))
    return {
        "opened_positions": len(opened),
        "closed_positions": len(closed),
        "open_positions_estimated": open_positions,
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "total_paper_pnl": total_pnl,
        "average_closed_trade_paper_pnl": avg_pnl,
    }


def classify_day_status(summary: dict[str, Any], overlay: dict[str, Any], ledger_stats: dict[str, Any]) -> str:
    gate = str(overlay.get("gate", "")).upper()
    evaluator = str(summary.get("ledger_evaluator_status", "")).upper()
    if "KILL" in gate or "KILL" in evaluator:
        return "STOP_REVIEW_REQUIRED_PAPER_ONLY"
    if ledger_stats["closed_positions"] == 0 and ledger_stats["opened_positions"] == 0:
        return "NO_COMPLETED_TRADES_HOLD_MORE_DATA_REQUIRED"
    if "HOLD_MORE_DATA" in gate or "HOLD_MORE_DATA" in evaluator:
        return "HOLD_MORE_DATA_REQUIRED"
    if "REVIEW" in gate or "REACHED" in evaluator:
        return "FORWARD_REVIEW_REQUIRED"
    return "PAPER_VALIDATION_CONTINUE"


def build_daily_pack(inputs: ReportPackInputs) -> dict[str, Any]:
    assert_safety_contract()

    summary = read_json(inputs.supervisor_summary)
    overlay = read_json(inputs.overlay_json)
    reason_rows = read_csv_rows(inputs.reason_log)
    ledger_rows = read_csv_rows(inputs.paper_ledger)
    audit_rows = read_csv_rows(inputs.overlay_audit_csv)

    latest_reason = reason_rows[-1] if reason_rows else {}
    latest_audit = audit_rows[-1] if audit_rows else {}
    ledger_stats = aggregate_ledger(ledger_rows)
    day_status = classify_day_status(summary, overlay, ledger_stats)

    signal_generated = safe_bool(pick(summary.get("signal_generated"), latest_reason.get("signal_generated"), overlay.get("signal_generated"), default=False))
    action = str(pick(overlay.get("action"), latest_audit.get("action"), default="NOT_AVAILABLE"))
    gate = str(pick(overlay.get("gate"), latest_audit.get("gate"), summary.get("ledger_evaluator_status"), default="NOT_AVAILABLE"))
    pe_reason = str(pick(summary.get("pe_reason"), overlay.get("pe_reason"), latest_reason.get("pe_reason"), default="NOT_AVAILABLE"))

    pack = {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "day_label": inputs.day_label,
        "paper_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "profitability_claim": False,
        "locked_candidate": str(pick(summary.get("locked_candidate"), overlay.get("locked_candidate"), default=LOCKED_CANDIDATE)),
        "day_status": day_status,
        "signal_generated": signal_generated,
        "event": str(pick(summary.get("event"), overlay.get("event"), latest_reason.get("event"), default="")),
        "action": action,
        "gate": gate,
        "pe_reason": pe_reason,
        "entry": pick(summary.get("entry"), overlay.get("entry"), latest_reason.get("entry"), default=""),
        "stop_loss": pick(summary.get("stop_loss"), overlay.get("stop_loss"), latest_reason.get("stop_loss"), default=""),
        "target": pick(summary.get("target"), overlay.get("target"), latest_reason.get("target"), default=""),
        "exit_reason": pick(summary.get("exit_reason"), overlay.get("exit_reason"), latest_reason.get("exit_reason"), default=""),
        "paper_pnl": pick(summary.get("paper_pnl"), overlay.get("paper_pnl"), latest_reason.get("paper_pnl"), default="0.0"),
        "position_state": str(pick(summary.get("position_state"), overlay.get("position_state"), latest_reason.get("position_state"), default="UNKNOWN")),
        "ledger_evaluator_status": str(summary.get("ledger_evaluator_status", "")),
        "plain_hinglish_reason": str(overlay.get("plain_hinglish_reason", "")),
        "operator_message": str(overlay.get("operator_message", "")),
        "ledger_stats": ledger_stats,
        "evidence_counts": {
            "reason_log_rows": len(reason_rows),
            "ledger_rows": len(ledger_rows),
            "overlay_audit_rows": len(audit_rows),
            "supervisor_report_present": inputs.supervisor_report is not None and inputs.supervisor_report.exists(),
            "overlay_report_present": inputs.overlay_report is not None and inputs.overlay_report.exists(),
        },
        "source_files": {
            "supervisor_summary": "" if inputs.supervisor_summary is None else str(inputs.supervisor_summary),
            "supervisor_report": "" if inputs.supervisor_report is None else str(inputs.supervisor_report),
            "reason_log": "" if inputs.reason_log is None else str(inputs.reason_log),
            "paper_ledger": "" if inputs.paper_ledger is None else str(inputs.paper_ledger),
            "overlay_json": "" if inputs.overlay_json is None else str(inputs.overlay_json),
            "overlay_report": "" if inputs.overlay_report is None else str(inputs.overlay_report),
            "overlay_audit_csv": "" if inputs.overlay_audit_csv is None else str(inputs.overlay_audit_csv),
        },
    }
    return pack


def write_daily_pack(out_dir: Path, pack: dict[str, Any]) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"
    report_path = out_dir / "MODULE_133_DAILY_PAPER_TRADING_REPORT.md"
    summary_csv = out_dir / "MODULE_133_DAILY_SUMMARY.csv"
    manifest_csv = out_dir / "MODULE_133_EVIDENCE_MANIFEST.csv"
    handover_path = out_dir / "MODULE_133_NEXT_DRY_RUN_HANDOVER.md"

    json_path.write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    stats = pack["ledger_stats"]
    evidence = pack["evidence_counts"]
    source_files = pack["source_files"]

    report_lines = [
        f"# HQE Module {MODULE_ID} - {MODULE_NAME}",
        "",
        "## Safety",
        "- Paper/simulation only: YES",
        "- Broker execution: NO",
        "- Real orders: NO",
        "- Real money approval: NO",
        "- Auto trading: NO",
        "- Option selling: NO",
        "- Profitability claim: NO",
        "",
        "## Day Summary",
        f"- Day label: {pack['day_label']}",
        f"- Day status: {pack['day_status']}",
        f"- Locked candidate: {pack['locked_candidate']}",
        f"- Signal generated: {pack['signal_generated']}",
        f"- Event: {pack['event']}",
        f"- AI overlay action: {pack['action']}",
        f"- Gate: {pack['gate']}",
        f"- Position state: {pack['position_state']}",
        f"- Ledger/evaluator status: {pack['ledger_evaluator_status']}",
        "",
        "## Trade Plan / Result",
        f"- PE reason: {pack['pe_reason']}",
        f"- Entry: {pack['entry']}",
        f"- SL: {pack['stop_loss']}",
        f"- Target: {pack['target']}",
        f"- Exit reason: {pack['exit_reason']}",
        f"- Paper PnL: {pack['paper_pnl']}",
        "",
        "## Ledger Stats",
        f"- Opened positions: {stats['opened_positions']}",
        f"- Closed positions: {stats['closed_positions']}",
        f"- Estimated open positions: {stats['open_positions_estimated']}",
        f"- Wins: {stats['wins']}",
        f"- Losses: {stats['losses']}",
        f"- Flats: {stats['flats']}",
        f"- Total paper PnL: {stats['total_paper_pnl']}",
        f"- Average closed trade paper PnL: {stats['average_closed_trade_paper_pnl']}",
        "",
        "## Plain Reason",
        pack.get("plain_hinglish_reason") or "No overlay reason available.",
        "",
        "## Operator Message",
        pack.get("operator_message") or "No operator message available.",
        "",
        "## Evidence Counts",
        f"- Reason log rows: {evidence['reason_log_rows']}",
        f"- Ledger rows: {evidence['ledger_rows']}",
        f"- Overlay audit rows: {evidence['overlay_audit_rows']}",
        f"- Supervisor report present: {evidence['supervisor_report_present']}",
        f"- Overlay report present: {evidence['overlay_report_present']}",
        "",
        "## Source Files",
    ]
    for name, path in source_files.items():
        report_lines.append(f"- {name}: {path}")
    report_lines.extend(
        [
            "",
            "## Rule",
            "This pack is forward paper-only evidence. It is not a profitability claim and not a real-money approval.",
        ]
    )
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    summary_fields = [
        "created_at",
        "day_label",
        "day_status",
        "locked_candidate",
        "signal_generated",
        "event",
        "action",
        "gate",
        "position_state",
        "entry",
        "stop_loss",
        "target",
        "exit_reason",
        "paper_pnl",
        "opened_positions",
        "closed_positions",
        "total_paper_pnl",
        "ledger_evaluator_status",
        "paper_only",
        "broker_execution_allowed",
        "real_orders_allowed",
        "auto_trading_allowed",
        "real_money_allowed",
    ]
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerow(
            {
                "created_at": pack["created_at"],
                "day_label": pack["day_label"],
                "day_status": pack["day_status"],
                "locked_candidate": pack["locked_candidate"],
                "signal_generated": pack["signal_generated"],
                "event": pack["event"],
                "action": pack["action"],
                "gate": pack["gate"],
                "position_state": pack["position_state"],
                "entry": pack["entry"],
                "stop_loss": pack["stop_loss"],
                "target": pack["target"],
                "exit_reason": pack["exit_reason"],
                "paper_pnl": pack["paper_pnl"],
                "opened_positions": stats["opened_positions"],
                "closed_positions": stats["closed_positions"],
                "total_paper_pnl": stats["total_paper_pnl"],
                "ledger_evaluator_status": pack["ledger_evaluator_status"],
                "paper_only": True,
                "broker_execution_allowed": False,
                "real_orders_allowed": False,
                "auto_trading_allowed": False,
                "real_money_allowed": False,
            }
        )

    with manifest_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["artifact", "path", "present"])
        writer.writeheader()
        for artifact, path in source_files.items():
            writer.writerow({"artifact": artifact, "path": path, "present": bool(path and Path(path).exists())})
        writer.writerow({"artifact": "daily_pack_json", "path": str(json_path), "present": json_path.exists()})
        writer.writerow({"artifact": "daily_report_md", "path": str(report_path), "present": report_path.exists()})
        writer.writerow({"artifact": "daily_summary_csv", "path": str(summary_csv), "present": summary_csv.exists()})

    handover_lines = [
        "# HQE Module 133 Next Dry Run Handover",
        "",
        "Status: Daily paper trading report pack generated.",
        "",
        "Next roadmap step before UI:",
        "1. Dry run 1",
        "2. Dry run 2 if needed",
        "3. Then UI dashboard",
        "",
        "Safety remains:",
        "- Paper/simulation only",
        "- Real money NO",
        "- Broker execution NO",
        "- Real orders NO",
        "- Auto trading NO",
        "- Option selling NO",
        "- No profitability claim",
        "",
        f"Daily report: {report_path}",
        f"Daily JSON: {json_path}",
        f"Daily CSV: {summary_csv}",
        f"Evidence manifest: {manifest_csv}",
    ]
    handover_path.write_text("\n".join(handover_lines) + "\n", encoding="utf-8")

    return {
        "daily_pack_json": str(json_path),
        "daily_report_md": str(report_path),
        "daily_summary_csv": str(summary_csv),
        "evidence_manifest_csv": str(manifest_csv),
        "next_dry_run_handover": str(handover_path),
    }


def default_out_dir(day_label: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_day = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in day_label)
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK_{safe_day}_{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--day-label", default=date.today().isoformat())
    parser.add_argument("--supervisor-summary", type=Path, default=None)
    parser.add_argument("--supervisor-report", type=Path, default=None)
    parser.add_argument("--reason-log", type=Path, default=None)
    parser.add_argument("--paper-ledger", type=Path, default=None)
    parser.add_argument("--overlay-json", type=Path, default=None)
    parser.add_argument("--overlay-report", type=Path, default=None)
    parser.add_argument("--overlay-audit-csv", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = args.out_dir or default_out_dir(args.day_label)
    inputs = ReportPackInputs(
        day_label=args.day_label,
        supervisor_summary=args.supervisor_summary,
        supervisor_report=args.supervisor_report,
        reason_log=args.reason_log,
        paper_ledger=args.paper_ledger,
        overlay_json=args.overlay_json,
        overlay_report=args.overlay_report,
        overlay_audit_csv=args.overlay_audit_csv,
        out_dir=out_dir,
    )
    pack = build_daily_pack(inputs)
    files = write_daily_pack(out_dir, pack)
    result = {**pack, **files, "out_dir": str(out_dir)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
