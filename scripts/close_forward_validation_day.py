#!/usr/bin/env python3
"""
HQE Module 145 - Forward Validation Day Ledger Closer / Zero-Trade Day Recorder

Purpose:
- Close one forward paper validation day honestly.
- Count actual rows in DAY_NNN_FORWARD_TRADE_LOG.csv.
- Record a separate day-level close ledger row, including zero-trade days.
- Link latest Module 140 daily workflow and Module 144 control-center evidence.
- Keep FORWARD_VALIDATION_MASTER_LEDGER.csv as a trade-level ledger.
- Never create fake trades.

Safety lock:
- Paper/simulation only.
- No real money.
- No broker execution.
- No real orders.
- No auto trading.
- No option selling.
- No external API.
- No profitability claim.

Important:
- Zero-trade day closure is written to FORWARD_VALIDATION_DAY_LEDGER.csv.
- Master trade ledger is not updated for zero-trade days.
- Master trade ledger can be synced only from actual day trade-log rows.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


MODULE_NAME = "Module 145 - Forward Validation Day Ledger Closer / Zero-Trade Day Recorder"

SAFETY_LOCK: Dict[str, Any] = {
    "paper_simulation_only": True,
    "real_money": False,
    "broker_execution": False,
    "real_orders": False,
    "auto_trading": False,
    "option_selling": False,
    "external_api": False,
    "profitability_claim": False,
    "fake_trades": False,
    "candidate_tuning": False,
    "note": (
        "This day closer records day-level evidence only. It does not place orders, "
        "connect to brokers, call external APIs, tune the candidate, or claim profitability."
    ),
}

TRADE_LEDGER_COLUMNS = [
    "date",
    "day_number",
    "trade_number",
    "expiry_week",
    "symbol",
    "side",
    "entry_time",
    "entry_price",
    "exit_time",
    "exit_price",
    "quantity",
    "gross_pnl",
    "estimated_charges",
    "net_pnl",
    "exit_reason",
    "rule_match",
    "data_quality_ok",
    "manual_override",
    "notes",
]

DAY_LEDGER_COLUMNS = [
    "date",
    "day_number",
    "day_status",
    "trade_count",
    "gross_pnl",
    "estimated_charges",
    "net_pnl",
    "distinct_expiry_weeks",
    "trade_log_path",
    "master_ledger_path",
    "module140_evidence_path",
    "module144_evidence_path",
    "data_quality_ok",
    "manual_override",
    "candidate_tuning",
    "safety_ok",
    "notes",
    "closed_at",
]

MODULE_140_DIR_HINT = "HQE_MODULE_140_DAILY_WORKFLOW_"
MODULE_144_DIR_HINT = "HQE_MODULE_144_OPERATOR_CONTROL_CENTER_"


@dataclass(frozen=True)
class DayCloseResult:
    active_dir: Path
    day_number: int
    trading_date: str
    trade_log_path: Path
    master_ledger_path: Path
    day_ledger_path: Path
    day_status: str
    trade_count: int
    gross_pnl: float
    estimated_charges: float
    net_pnl: float
    distinct_expiry_weeks: List[str]
    master_rows_appended: int
    module140_evidence_path: Optional[Path]
    module144_evidence_path: Optional[Path]
    json_path: Path
    markdown_path: Path
    day_ledger_csv_path: Path
    safety_lock: Dict[str, Any]
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": MODULE_NAME,
            "closed_at": datetime.now().isoformat(timespec="seconds"),
            "active_dir": str(self.active_dir),
            "day_number": self.day_number,
            "trading_date": self.trading_date,
            "trade_log_path": str(self.trade_log_path),
            "master_ledger_path": str(self.master_ledger_path),
            "day_ledger_path": str(self.day_ledger_path),
            "day_status": self.day_status,
            "trade_count": self.trade_count,
            "gross_pnl": self.gross_pnl,
            "estimated_charges": self.estimated_charges,
            "net_pnl": self.net_pnl,
            "distinct_expiry_weeks": self.distinct_expiry_weeks,
            "master_rows_appended": self.master_rows_appended,
            "module140_evidence_path": str(self.module140_evidence_path) if self.module140_evidence_path else None,
            "module144_evidence_path": str(self.module144_evidence_path) if self.module144_evidence_path else None,
            "json_path": str(self.json_path),
            "markdown_path": str(self.markdown_path),
            "day_ledger_csv_path": str(self.day_ledger_csv_path),
            "safety_lock": self.safety_lock,
            "notes": self.notes,
        }


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _today_iso() -> str:
    return date.today().isoformat()


def _day_prefix(day_number: int) -> str:
    return f"DAY_{day_number:03d}"


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if text == "":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _normalize_bool_text(value: Any) -> str:
    text = str(value).strip().upper()
    if text in {"TRUE", "YES", "1", "Y"}:
        return "YES"
    if text in {"FALSE", "NO", "0", "N"}:
        return "NO"
    return text or "UNKNOWN"


def _normalize_csv_header(value: Any) -> str:
    """Normalize CSV headers from Windows/PowerShell-created files.

    PowerShell and Excel-style tools may write a UTF-8 BOM. Without utf-8-sig
    handling, the first header can become "\ufeffdate" instead of "date".
    """
    return str(value or "").replace("\ufeff", "").strip()


def read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(str(path))

    # utf-8-sig safely handles both normal UTF-8 and BOM-prefixed UTF-8 CSVs.
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        raw_headers = list(reader.fieldnames or [])
        headers = [_normalize_csv_header(header) for header in raw_headers]

        rows: List[Dict[str, str]] = []
        for raw_row in reader:
            normalized_row: Dict[str, str] = {}
            for key, value in raw_row.items():
                normalized_key = _normalize_csv_header(key)
                if normalized_key:
                    normalized_row[normalized_key] = value
            rows.append(normalized_row)

    return headers, rows


def write_csv_rows(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", errors="replace", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def append_csv_rows(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8", errors="replace", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def validate_trade_log_schema(headers: Sequence[str]) -> List[str]:
    return [col for col in TRADE_LEDGER_COLUMNS if col not in headers]


def summarize_trade_rows(rows: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    gross = sum(_safe_float(row.get("gross_pnl")) for row in rows)
    charges = sum(_safe_float(row.get("estimated_charges")) for row in rows)
    net = sum(_safe_float(row.get("net_pnl")) for row in rows)
    expiry_weeks = sorted({str(row.get("expiry_week", "")).strip() for row in rows if str(row.get("expiry_week", "")).strip()})

    manual_override_values = {_normalize_bool_text(row.get("manual_override")) for row in rows}
    data_quality_values = {_normalize_bool_text(row.get("data_quality_ok")) for row in rows}

    return {
        "trade_count": len(rows),
        "gross_pnl": gross,
        "estimated_charges": charges,
        "net_pnl": net,
        "distinct_expiry_weeks": expiry_weeks,
        "manual_override_values": sorted(manual_override_values),
        "data_quality_values": sorted(data_quality_values),
    }


def find_latest_dir(root: Path, name_prefix: str) -> Optional[Path]:
    if not root.exists() or not root.is_dir():
        return None

    candidates = [path for path in root.iterdir() if path.is_dir() and path.name.startswith(name_prefix)]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_existing_day_ledger(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        return list(DAY_LEDGER_COLUMNS), []
    headers, rows = read_csv_rows(path)
    if not headers:
        return list(DAY_LEDGER_COLUMNS), rows
    merged_headers = list(headers)
    for col in DAY_LEDGER_COLUMNS:
        if col not in merged_headers:
            merged_headers.append(col)
    return merged_headers, rows


def dedupe_day_ledger_rows(rows: Sequence[Dict[str, Any]], trading_date: str, day_number: int) -> List[Dict[str, Any]]:
    return [
        row
        for row in rows
        if not (
            str(row.get("date", "")).strip() == trading_date
            and str(row.get("day_number", "")).strip() == str(day_number)
        )
    ]


def trade_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(row.get("date", "")).strip(),
        str(row.get("day_number", "")).strip(),
        str(row.get("trade_number", "")).strip(),
    )


def sync_actual_trades_to_master(
    master_ledger_path: Path,
    trade_rows: Sequence[Dict[str, str]],
    sync_master_ledger: bool,
) -> int:
    if not sync_master_ledger or not trade_rows:
        return 0

    if master_ledger_path.exists():
        master_headers, master_rows = read_csv_rows(master_ledger_path)
    else:
        master_headers, master_rows = list(TRADE_LEDGER_COLUMNS), []

    missing = validate_trade_log_schema(master_headers)
    if missing:
        raise ValueError(f"Master ledger schema missing columns: {missing}")

    existing_keys = {trade_key(row) for row in master_rows}
    rows_to_append: List[Dict[str, Any]] = []
    for row in trade_rows:
        key = trade_key(row)
        if key in existing_keys:
            continue
        rows_to_append.append(row)

    if rows_to_append:
        append_csv_rows(master_ledger_path, TRADE_LEDGER_COLUMNS, rows_to_append)

    return len(rows_to_append)


def render_markdown(result: DayCloseResult) -> str:
    lines: List[str] = []
    lines.append(f"# {MODULE_NAME}")
    lines.append("")
    lines.append(f"Closed at: `{datetime.now().isoformat(timespec='seconds')}`")
    lines.append(f"Day status: `{result.day_status}`")
    lines.append("")
    lines.append("## Safety Lock")
    lines.append("")
    lines.append("- Paper/simulation only: `YES`")
    lines.append("- Real money: `NO`")
    lines.append("- Broker execution: `NO`")
    lines.append("- Real orders: `NO`")
    lines.append("- Auto trading: `NO`")
    lines.append("- Option selling: `NO`")
    lines.append("- External API: `NO`")
    lines.append("- Profitability claim: `NO`")
    lines.append("- Fake trades: `NO`")
    lines.append("- Candidate tuning: `NO`")
    lines.append("")
    lines.append("> This is not a profitability claim. Zero-trade days are recorded as day-level evidence, not fake trades.")
    lines.append("")
    lines.append("## Day Summary")
    lines.append("")
    lines.append(f"- Trading date: `{result.trading_date}`")
    lines.append(f"- Day number: `{result.day_number}`")
    lines.append(f"- Trade count: `{result.trade_count}`")
    lines.append(f"- Gross PnL: `{result.gross_pnl}`")
    lines.append(f"- Estimated charges: `{result.estimated_charges}`")
    lines.append(f"- Net PnL: `{result.net_pnl}`")
    lines.append(f"- Distinct expiry weeks from actual trades: `{', '.join(result.distinct_expiry_weeks) if result.distinct_expiry_weeks else 'NONE'}`")
    lines.append(f"- Master rows appended: `{result.master_rows_appended}`")
    lines.append("")
    lines.append("## Evidence Links")
    lines.append("")
    lines.append(f"- Trade log: `{result.trade_log_path}`")
    lines.append(f"- Master trade ledger: `{result.master_ledger_path}`")
    lines.append(f"- Day close ledger: `{result.day_ledger_path}`")
    lines.append(f"- Module 140 evidence: `{result.module140_evidence_path}`")
    lines.append(f"- Module 144 evidence: `{result.module144_evidence_path}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(result.notes)
    lines.append("")
    lines.append("## Operator Handoff")
    lines.append("")
    lines.append("```text")
    lines.append("Module 145 handoff:")
    lines.append("- Day status:")
    lines.append("- Trading date:")
    lines.append("- Day number:")
    lines.append("- Trade count:")
    lines.append("- Day ledger:")
    lines.append("- Close report:")
    lines.append("- Master ledger updated with actual trades only: YES / NO")
    lines.append("- Real money/broker/orders/auto trading/option selling: all NO")
    lines.append("- Profitability claim: NO")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def close_forward_validation_day(
    active_dir: Path,
    day_number: int = 1,
    trading_date: Optional[str] = None,
    runs_root: Optional[Path] = None,
    module140_dir: Optional[Path] = None,
    module144_dir: Optional[Path] = None,
    sync_master_ledger: bool = False,
    notes: str = "",
) -> Dict[str, Any]:
    active_dir = active_dir.expanduser()
    if not active_dir.exists() or not active_dir.is_dir():
        raise FileNotFoundError(f"Active validation folder missing: {active_dir}")

    trading_date = trading_date or _today_iso()
    runs_root = runs_root.expanduser() if runs_root else active_dir.parent

    day_prefix = _day_prefix(day_number)
    trade_log_path = active_dir / f"{day_prefix}_FORWARD_TRADE_LOG.csv"
    master_ledger_path = active_dir / "FORWARD_VALIDATION_MASTER_LEDGER.csv"
    day_ledger_path = active_dir / "FORWARD_VALIDATION_DAY_LEDGER.csv"

    headers, trade_rows = read_csv_rows(trade_log_path)
    missing_cols = validate_trade_log_schema(headers)
    if missing_cols:
        raise ValueError(f"Trade log schema missing columns: {missing_cols}")

    summary = summarize_trade_rows(trade_rows)

    if summary["trade_count"] == 0:
        day_status = "ZERO_TRADE_DAY_RECORDED"
        safety_notes = "No trade rows found. Recorded honest zero-trade day-level evidence only; no master trade row was created."
    else:
        day_status = "TRADE_DAY_RECORDED"
        safety_notes = "Actual trade rows found in day trade log. Master ledger sync appends only real trade-log rows when enabled."

    manual_override = "NO"
    if "YES" in summary["manual_override_values"]:
        manual_override = "YES"

    data_quality_ok = "YES"
    if trade_rows and any(value not in {"YES", "TRUE", "1"} for value in summary["data_quality_values"]):
        data_quality_ok = "REVIEW"

    if not module140_dir:
        module140_dir = find_latest_dir(runs_root, MODULE_140_DIR_HINT)
    if not module144_dir:
        module144_dir = find_latest_dir(runs_root, MODULE_144_DIR_HINT)

    module140_evidence_path = module140_dir / "MODULE_140_DAILY_WORKFLOW_MODEL.json" if module140_dir else None
    if module140_evidence_path and not module140_evidence_path.exists():
        module140_evidence_path = module140_dir / "MODULE_140_DAILY_WORKFLOW_REPORT.md" if module140_dir else None

    module144_evidence_path = module144_dir / "MODULE_144_OPERATOR_CONTROL_CENTER.json" if module144_dir else None
    if module144_evidence_path and not module144_evidence_path.exists():
        module144_evidence_path = module144_dir / "MODULE_144_OPERATOR_CONTROL_CENTER.md" if module144_dir else None

    master_rows_appended = sync_actual_trades_to_master(
        master_ledger_path=master_ledger_path,
        trade_rows=trade_rows,
        sync_master_ledger=sync_master_ledger,
    )

    day_ledger_headers, existing_day_rows = load_existing_day_ledger(day_ledger_path)
    day_row = {
        "date": trading_date,
        "day_number": str(day_number),
        "day_status": day_status,
        "trade_count": str(summary["trade_count"]),
        "gross_pnl": f"{summary['gross_pnl']:.2f}",
        "estimated_charges": f"{summary['estimated_charges']:.2f}",
        "net_pnl": f"{summary['net_pnl']:.2f}",
        "distinct_expiry_weeks": "|".join(summary["distinct_expiry_weeks"]),
        "trade_log_path": str(trade_log_path),
        "master_ledger_path": str(master_ledger_path),
        "module140_evidence_path": str(module140_evidence_path) if module140_evidence_path else "",
        "module144_evidence_path": str(module144_evidence_path) if module144_evidence_path else "",
        "data_quality_ok": data_quality_ok,
        "manual_override": manual_override,
        "candidate_tuning": "NO",
        "safety_ok": "YES",
        "notes": (notes or safety_notes),
        "closed_at": datetime.now().isoformat(timespec="seconds"),
    }

    final_rows = dedupe_day_ledger_rows(existing_day_rows, trading_date, day_number)
    final_rows.append(day_row)
    write_csv_rows(day_ledger_path, day_ledger_headers, final_rows)

    close_json_path = active_dir / f"{day_prefix}_FORWARD_VALIDATION_DAY_CLOSE.json"
    close_md_path = active_dir / f"{day_prefix}_FORWARD_VALIDATION_DAY_CLOSE.md"

    result = DayCloseResult(
        active_dir=active_dir,
        day_number=day_number,
        trading_date=trading_date,
        trade_log_path=trade_log_path,
        master_ledger_path=master_ledger_path,
        day_ledger_path=day_ledger_path,
        day_status=day_status,
        trade_count=int(summary["trade_count"]),
        gross_pnl=float(summary["gross_pnl"]),
        estimated_charges=float(summary["estimated_charges"]),
        net_pnl=float(summary["net_pnl"]),
        distinct_expiry_weeks=list(summary["distinct_expiry_weeks"]),
        master_rows_appended=master_rows_appended,
        module140_evidence_path=module140_evidence_path,
        module144_evidence_path=module144_evidence_path,
        json_path=close_json_path,
        markdown_path=close_md_path,
        day_ledger_csv_path=day_ledger_path,
        safety_lock=SAFETY_LOCK,
        notes=(notes or safety_notes),
    )

    result_dict = result.to_dict()
    close_json_path.write_text(json.dumps(result_dict, indent=2, default=_json_default), encoding="utf-8")
    close_md_path.write_text(render_markdown(result), encoding="utf-8")

    return result_dict


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--active-dir", required=True, help="Active forward validation folder.")
    parser.add_argument("--day-number", type=int, default=1, help="Forward validation day number.")
    parser.add_argument("--trading-date", default=None, help="Trading date in YYYY-MM-DD. Defaults to local today.")
    parser.add_argument("--runs-root", default=None, help="Runs root used to auto-link latest Module 140/144 evidence.")
    parser.add_argument("--module140-dir", default=None, help="Explicit Module 140 daily workflow folder.")
    parser.add_argument("--module144-dir", default=None, help="Explicit Module 144 control-center folder.")
    parser.add_argument(
        "--sync-master-ledger",
        action="store_true",
        help="Append actual day trade-log rows to master trade ledger. Zero-trade days never create master trade rows.",
    )
    parser.add_argument("--notes", default="", help="Optional operator notes for this day close.")
    parser.add_argument("--print-summary", action="store_true", help="Print concise day close status and paths.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    result = close_forward_validation_day(
        active_dir=Path(args.active_dir),
        day_number=args.day_number,
        trading_date=args.trading_date,
        runs_root=Path(args.runs_root) if args.runs_root else None,
        module140_dir=Path(args.module140_dir) if args.module140_dir else None,
        module144_dir=Path(args.module144_dir) if args.module144_dir else None,
        sync_master_ledger=args.sync_master_ledger,
        notes=args.notes,
    )

    if args.print_summary:
        print("MODULE_145_FORWARD_VALIDATION_DAY_CLOSED")
        print(f"day_status={result['day_status']}")
        print(f"trading_date={result['trading_date']}")
        print(f"day_number={result['day_number']}")
        print(f"trade_count={result['trade_count']}")
        print(f"net_pnl={result['net_pnl']}")
        print(f"master_rows_appended={result['master_rows_appended']}")
        print(f"day_ledger={result['day_ledger_path']}")
        print(f"json={result['json_path']}")
        print(f"markdown={result['markdown_path']}")
        print("safety=paper_only_no_broker_no_real_orders_no_auto_trading_no_option_selling_no_external_api_no_profitability_claim_no_fake_trades")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
