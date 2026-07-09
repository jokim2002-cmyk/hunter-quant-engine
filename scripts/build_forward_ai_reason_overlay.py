"""
Module 132: Forward AI Reason Overlay

Deterministic, local, paper-only reason overlay for HQE forward paper validation.

Important:
- No external AI/API call
- No broker execution
- No real orders
- No real money approval
- No auto trading
- Converts Module 131 paper supervisor output into clear reason/audit reports
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


MODULE_ID = 132
MODULE_NAME = "Forward AI Reason Overlay"

PAPER_ONLY = True
EXTERNAL_AI_API_ALLOWED = False
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
REAL_MONEY_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False

LOCKED_CANDIDATE = "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120"


@dataclass(frozen=True)
class OverlayInputs:
    supervisor_summary: Path | None
    reason_log: Path | None
    state_json: Path | None
    out_dir: Path


def assert_safety_contract() -> None:
    blocked = {
        "EXTERNAL_AI_API_ALLOWED": EXTERNAL_AI_API_ALLOWED,
        "BROKER_EXECUTION_ALLOWED": BROKER_EXECUTION_ALLOWED,
        "REAL_ORDERS_ALLOWED": REAL_ORDERS_ALLOWED,
        "REAL_MONEY_ALLOWED": REAL_MONEY_ALLOWED,
        "AUTO_TRADING_ALLOWED": AUTO_TRADING_ALLOWED,
        "OPTION_SELLING_ALLOWED": OPTION_SELLING_ALLOWED,
    }
    if not PAPER_ONLY:
        raise RuntimeError("SAFETY_FAIL: PAPER_ONLY must stay True.")
    enabled = [name for name, value in blocked.items() if value]
    if enabled:
        raise RuntimeError("SAFETY_FAIL: blocked capability enabled: " + ",".join(enabled))


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return {}
    return payload


def read_latest_csv_row(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {}
    return {str(k): "" if v is None else str(v) for k, v in rows[-1].items()}


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "yes", "1", "y"}


def pick(*values: Any, default: Any = "") -> Any:
    for value in values:
        if value is not None and str(value).strip() != "":
            return value
    return default


def classify_action(summary: dict[str, Any], reason_row: dict[str, str], state: dict[str, Any]) -> str:
    data_ready = boolish(pick(summary.get("data_ready"), reason_row.get("data_ready"), default=False))
    signal_generated = boolish(
        pick(summary.get("signal_generated"), reason_row.get("signal_generated"), default=False)
    )
    event = str(pick(summary.get("event"), reason_row.get("event"), default="")).upper()
    state_status = str(pick(summary.get("position_state"), state.get("status"), default="UNKNOWN")).upper()

    if not data_ready:
        return "WAIT_DATA_NOT_READY_PAPER_ONLY"
    if event == "POSITION_CLOSED":
        return "POSITION_CLOSED_PAPER_ONLY_REVIEW_PNL"
    if event == "POSITION_HELD" or state_status == "OPEN" and not signal_generated:
        return "HOLD_OPEN_PAPER_POSITION"
    if signal_generated or event == "POSITION_OPENED":
        return "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY"
    return "NO_TRADE_SIGNAL_REJECTED_PAPER_ONLY"


def classify_gate(summary: dict[str, Any]) -> str:
    status = str(summary.get("ledger_evaluator_status", "")).upper()
    if "KILL" in status:
        return "STOP_REVIEW_REQUIRED"
    if "HOLD_MORE_DATA" in status or "0_OF_30" in status:
        return "HOLD_MORE_DATA_REQUIRED"
    if "REACHED" in status:
        return "FORWARD_REVIEW_REQUIRED"
    return "PAPER_AUDIT_CONTINUE"


def build_plain_reason(
    action: str,
    summary: dict[str, Any],
    reason_row: dict[str, str],
    state: dict[str, Any],
) -> str:
    pe_reason = str(pick(summary.get("pe_reason"), reason_row.get("pe_reason"), default="Reason not available"))
    entry = pick(summary.get("entry"), reason_row.get("entry"), state.get("entry"), default="")
    stop_loss = pick(summary.get("stop_loss"), reason_row.get("stop_loss"), state.get("stop_loss"), default="")
    target = pick(summary.get("target"), reason_row.get("target"), state.get("target"), default="")
    exit_reason = pick(summary.get("exit_reason"), reason_row.get("exit_reason"), state.get("last_exit_reason"), default="")
    paper_pnl = pick(summary.get("paper_pnl"), reason_row.get("paper_pnl"), state.get("last_paper_pnl"), default="0.0")
    ledger_status = str(summary.get("ledger_evaluator_status", "Ledger status not available"))

    if action == "WAIT_DATA_NOT_READY_PAPER_ONLY":
        return (
            "Data abhi ready nahi hai, isliye paper supervisor wait mode me rahega. "
            f"Reason: {pe_reason}. Koi broker order, real order, ya auto trade allowed nahi hai."
        )

    if action == "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY":
        return (
            "Locked candidate ne PE buy paper signal accept kiya hai. "
            f"Reason chain: {pe_reason}. Entry {entry}, SL {stop_loss}, target {target}. "
            f"Ledger status: {ledger_status}. Ye sirf simulated paper position hai."
        )

    if action == "HOLD_OPEN_PAPER_POSITION":
        return (
            "Paper position open/hold state me hai. System SL/target/EOD paper exit ka wait karega. "
            f"Entry {entry}, SL {stop_loss}, target {target}. Koi real execution allowed nahi hai."
        )

    if action == "POSITION_CLOSED_PAPER_ONLY_REVIEW_PNL":
        return (
            "Paper position close ho gayi hai. "
            f"Exit reason: {exit_reason}. Paper PnL: {paper_pnl}. "
            "Is result ko forward validation ledger me sirf evidence ke liye use karna hai."
        )

    return (
        "Is cycle me trade reject/no-signal hai. "
        f"Reason chain: {pe_reason}. System wait karega aur next 5-minute paper cycle me fresh data check karega."
    )


def build_operator_message(action: str, gate: str) -> str:
    if gate == "STOP_REVIEW_REQUIRED":
        return "STOP. Paper evidence me risk/kill condition dikhi. Manual review required. Real money still NO."
    if action == "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY":
        return "Paper PE signal logged. Position simulated only. Real order mat lagana."
    if action == "HOLD_OPEN_PAPER_POSITION":
        return "Open paper position ko monitor karo. SL/target/EOD rule ke bina manual exit claim mat banana."
    if action == "POSITION_CLOSED_PAPER_ONLY_REVIEW_PNL":
        return "Closed paper result ko ledger/evaluator me audit karo. Live/P&L claim mat banana."
    return "No action for real market. Paper supervisor ko next cycle tak wait karne do."


def build_overlay(inputs: OverlayInputs) -> dict[str, Any]:
    assert_safety_contract()

    summary = read_json(inputs.supervisor_summary)
    reason_row = read_latest_csv_row(inputs.reason_log)
    state = read_json(inputs.state_json)

    action = classify_action(summary, reason_row, state)
    gate = classify_gate(summary)
    plain_reason = build_plain_reason(action, summary, reason_row, state)
    operator_message = build_operator_message(action, gate)

    overlay = {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "paper_only": True,
        "external_ai_api_allowed": False,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "profitability_claim": False,
        "locked_candidate": str(summary.get("locked_candidate", LOCKED_CANDIDATE)),
        "action": action,
        "gate": gate,
        "signal_generated": boolish(summary.get("signal_generated", reason_row.get("signal_generated", False))),
        "event": str(pick(summary.get("event"), reason_row.get("event"), default="")),
        "pe_reason": str(pick(summary.get("pe_reason"), reason_row.get("pe_reason"), default="")),
        "entry": pick(summary.get("entry"), reason_row.get("entry"), state.get("entry"), default=""),
        "stop_loss": pick(summary.get("stop_loss"), reason_row.get("stop_loss"), state.get("stop_loss"), default=""),
        "target": pick(summary.get("target"), reason_row.get("target"), state.get("target"), default=""),
        "exit_reason": pick(summary.get("exit_reason"), reason_row.get("exit_reason"), state.get("last_exit_reason"), default=""),
        "paper_pnl": pick(summary.get("paper_pnl"), reason_row.get("paper_pnl"), state.get("last_paper_pnl"), default="0.0"),
        "position_state": str(pick(summary.get("position_state"), reason_row.get("position_state"), state.get("status"), default="UNKNOWN")),
        "ledger_evaluator_status": str(summary.get("ledger_evaluator_status", "")),
        "plain_hinglish_reason": plain_reason,
        "operator_message": operator_message,
        "source_files": {
            "supervisor_summary": "" if inputs.supervisor_summary is None else str(inputs.supervisor_summary),
            "reason_log": "" if inputs.reason_log is None else str(inputs.reason_log),
            "state_json": "" if inputs.state_json is None else str(inputs.state_json),
        },
    }
    return overlay


def write_overlay_files(out_dir: Path, overlay: dict[str, Any]) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "MODULE_132_AI_REASON_OVERLAY.json"
    report_path = out_dir / "MODULE_132_AI_REASON_OVERLAY_REPORT.md"
    audit_csv = out_dir / "MODULE_132_DECISION_AUDIT.csv"

    json_path.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report_lines = [
        f"# HQE Module {MODULE_ID} - {MODULE_NAME}",
        "",
        "## Safety",
        "- Paper/simulation only: YES",
        "- External AI/API call: NO",
        "- Broker execution: NO",
        "- Real orders: NO",
        "- Real money approval: NO",
        "- Auto trading: NO",
        "- Option selling: NO",
        "- Profitability claim: NO",
        "",
        "## Locked Candidate",
        f"- {overlay['locked_candidate']}",
        "",
        "## AI Reason Overlay",
        f"- Action: {overlay['action']}",
        f"- Gate: {overlay['gate']}",
        f"- Event: {overlay['event']}",
        f"- Signal generated: {overlay['signal_generated']}",
        f"- PE reason: {overlay['pe_reason']}",
        f"- Entry: {overlay['entry']}",
        f"- SL: {overlay['stop_loss']}",
        f"- Target: {overlay['target']}",
        f"- Exit reason: {overlay['exit_reason']}",
        f"- Paper PnL: {overlay['paper_pnl']}",
        f"- Position state: {overlay['position_state']}",
        f"- Ledger/evaluator status: {overlay['ledger_evaluator_status']}",
        "",
        "## Plain Hinglish Reason",
        overlay["plain_hinglish_reason"],
        "",
        "## Operator Message",
        overlay["operator_message"],
        "",
        "## Rule",
        "This overlay is deterministic and local. It is not a profitability claim and not a trading recommendation.",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    fieldnames = [
        "created_at",
        "module",
        "action",
        "gate",
        "signal_generated",
        "event",
        "pe_reason",
        "entry",
        "stop_loss",
        "target",
        "exit_reason",
        "paper_pnl",
        "position_state",
        "ledger_evaluator_status",
        "paper_only",
        "broker_execution_allowed",
        "real_orders_allowed",
        "auto_trading_allowed",
        "real_money_allowed",
    ]
    with audit_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerow(overlay)

    return {
        "overlay_json": str(json_path),
        "overlay_report": str(report_path),
        "audit_csv": str(audit_csv),
    }


def default_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_132_AI_REASON_OVERLAY_{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--supervisor-summary", type=Path, default=None)
    parser.add_argument("--reason-log", type=Path, default=None)
    parser.add_argument("--state-json", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = args.out_dir or default_out_dir()
    inputs = OverlayInputs(
        supervisor_summary=args.supervisor_summary,
        reason_log=args.reason_log,
        state_json=args.state_json,
        out_dir=out_dir,
    )
    overlay = build_overlay(inputs)
    files = write_overlay_files(out_dir, overlay)
    result = {**overlay, **files}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

