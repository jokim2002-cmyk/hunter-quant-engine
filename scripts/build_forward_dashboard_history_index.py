
"""
Module 136: Dashboard History Index / Multiple-Day Selector

Local static read-only history index for multiple forward paper daily packs.

Safety:
- Paper/simulation only
- Read-only history index
- Local static HTML only
- No broker execution
- No real orders
- No real money approval
- No auto trading
- No option selling
- No external API
- No profitability claim
"""

from __future__ import annotations

import argparse
import csv
import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


MODULE_ID = 136
MODULE_NAME = "Dashboard History Index / Multiple-Day Selector"

PAPER_ONLY = True
READ_ONLY_HISTORY_INDEX = True
LOCAL_STATIC_HTML_ONLY = True
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
REAL_MONEY_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False
EXTERNAL_API_ALLOWED = False
PROFITABILITY_CLAIM = False

DAILY_PACK_NAME = "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"
DAILY_REPORT_NAME = "MODULE_133_DAILY_PAPER_TRADING_REPORT.md"
DAILY_SUMMARY_NAME = "MODULE_133_DAILY_SUMMARY.csv"
EVIDENCE_MANIFEST_NAME = "MODULE_133_EVIDENCE_MANIFEST.csv"
DASHBOARD_HTML_NAME = "MODULE_134_FORWARD_PAPER_DASHBOARD.html"


@dataclass(frozen=True)
class HistoryInputs:
    runs_root: Path
    out_dir: Path
    max_items: int = 50


def assert_safety_contract() -> None:
    if not PAPER_ONLY:
        raise RuntimeError("SAFETY_FAIL: PAPER_ONLY must stay True.")
    if not READ_ONLY_HISTORY_INDEX:
        raise RuntimeError("SAFETY_FAIL: history index must stay read-only.")
    if not LOCAL_STATIC_HTML_ONLY:
        raise RuntimeError("SAFETY_FAIL: history index must stay local static HTML only.")

    blocked = {
        "BROKER_EXECUTION_ALLOWED": BROKER_EXECUTION_ALLOWED,
        "REAL_ORDERS_ALLOWED": REAL_ORDERS_ALLOWED,
        "REAL_MONEY_ALLOWED": REAL_MONEY_ALLOWED,
        "AUTO_TRADING_ALLOWED": AUTO_TRADING_ALLOWED,
        "OPTION_SELLING_ALLOWED": OPTION_SELLING_ALLOWED,
        "EXTERNAL_API_ALLOWED": EXTERNAL_API_ALLOWED,
        "PROFITABILITY_CLAIM": PROFITABILITY_CLAIM,
    }
    enabled = [name for name, value in blocked.items() if value]
    if enabled:
        raise RuntimeError("SAFETY_FAIL: blocked capability enabled: " + ",".join(enabled))


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


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


def discover_daily_pack_paths(runs_root: Path) -> list[Path]:
    if not runs_root.exists() or not runs_root.is_dir():
        return []
    paths = [path for path in runs_root.rglob(DAILY_PACK_NAME) if path.is_file()]
    return sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True)


def find_optional_file(folder: Path, filename: str) -> str:
    path = folder / filename
    return str(path) if path.exists() else ""


def build_history_record(pack_path: Path) -> dict[str, Any]:
    pack = read_json(pack_path)
    folder = pack_path.parent

    ledger_stats = pack.get("ledger_stats", {})
    if not isinstance(ledger_stats, dict):
        ledger_stats = {}

    evidence_counts = pack.get("evidence_counts", {})
    if not isinstance(evidence_counts, dict):
        evidence_counts = {}

    return {
        "folder": str(folder),
        "modified_at": datetime.fromtimestamp(pack_path.stat().st_mtime).isoformat(timespec="seconds"),
        "day_label": str(pick(pack.get("day_label"), folder.name, default="UNKNOWN_DAY")),
        "day_status": str(pick(pack.get("day_status"), default="UNKNOWN")),
        "signal_generated": safe_bool(pack.get("signal_generated", False)),
        "event": str(pick(pack.get("event"), default="")),
        "action": str(pick(pack.get("action"), default="")),
        "gate": str(pick(pack.get("gate"), default="")),
        "position_state": str(pick(pack.get("position_state"), default="UNKNOWN")),
        "ledger_evaluator_status": str(pick(pack.get("ledger_evaluator_status"), default="")),
        "pe_reason": str(pick(pack.get("pe_reason"), default="")),
        "entry": pick(pack.get("entry"), default=""),
        "stop_loss": pick(pack.get("stop_loss"), default=""),
        "target": pick(pack.get("target"), default=""),
        "exit_reason": pick(pack.get("exit_reason"), default=""),
        "paper_pnl": safe_float(pack.get("paper_pnl"), 0.0),
        "opened_positions": int(safe_float(ledger_stats.get("opened_positions"), 0)),
        "closed_positions": int(safe_float(ledger_stats.get("closed_positions"), 0)),
        "open_positions_estimated": int(safe_float(ledger_stats.get("open_positions_estimated"), 0)),
        "total_paper_pnl": safe_float(ledger_stats.get("total_paper_pnl"), 0.0),
        "reason_log_rows": int(safe_float(evidence_counts.get("reason_log_rows"), 0)),
        "ledger_rows": int(safe_float(evidence_counts.get("ledger_rows"), 0)),
        "overlay_audit_rows": int(safe_float(evidence_counts.get("overlay_audit_rows"), 0)),
        "daily_pack_json": str(pack_path),
        "daily_report_md": find_optional_file(folder, DAILY_REPORT_NAME),
        "daily_summary_csv": find_optional_file(folder, DAILY_SUMMARY_NAME),
        "evidence_manifest_csv": find_optional_file(folder, EVIDENCE_MANIFEST_NAME),
        "dashboard_html": find_optional_file(folder, DASHBOARD_HTML_NAME),
    }


def build_history_model(inputs: HistoryInputs) -> dict[str, Any]:
    assert_safety_contract()

    all_paths = discover_daily_pack_paths(inputs.runs_root)
    selected_paths = all_paths[: max(1, int(inputs.max_items))]
    records = [build_history_record(path) for path in selected_paths]

    signal_days = len([record for record in records if record["signal_generated"]])
    no_signal_days = len(records) - signal_days
    open_positions = sum(int(record["open_positions_estimated"]) for record in records)
    closed_positions = sum(int(record["closed_positions"]) for record in records)
    total_paper_pnl = round(sum(float(record["total_paper_pnl"]) for record in records), 2)

    return {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "paper_only": True,
        "read_only_history_index": True,
        "local_static_html_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "external_api_allowed": False,
        "profitability_claim": False,
        "runs_root": str(inputs.runs_root),
        "history_status": "HISTORY_READY" if records else "NO_DAILY_PACKS_FOUND",
        "total_records": len(records),
        "total_discovered": len(all_paths),
        "max_items": max(1, int(inputs.max_items)),
        "summary": {
            "signal_days": signal_days,
            "no_signal_days": no_signal_days,
            "open_positions_estimated": open_positions,
            "closed_positions": closed_positions,
            "total_paper_pnl": total_paper_pnl,
        },
        "records": records,
    }


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def link_cell(path: str, label: str) -> str:
    if not path:
        return ""
    uri = Path(path).resolve().as_uri()
    return f'<a href="{esc(uri)}">{esc(label)}</a>'


def render_history_html(model: dict[str, Any]) -> str:
    summary = model["summary"]
    rows: list[str] = []

    for index, record in enumerate(model["records"], start=1):
        rows.append(
            f"""
<tr>
  <td>{index}</td>
  <td>{esc(record['modified_at'])}</td>
  <td>{esc(record['day_label'])}</td>
  <td>{esc(record['day_status'])}</td>
  <td>{esc(record['signal_generated'])}</td>
  <td>{esc(record['event'])}</td>
  <td>{esc(record['action'])}</td>
  <td>{esc(record['position_state'])}</td>
  <td>{esc(record['opened_positions'])}</td>
  <td>{esc(record['closed_positions'])}</td>
  <td>{esc(record['total_paper_pnl'])}</td>
  <td>{link_cell(record['daily_report_md'], 'Report')}</td>
  <td>{link_cell(record['daily_pack_json'], 'JSON')}</td>
  <td>{link_cell(record['dashboard_html'], 'Dashboard') if record['dashboard_html'] else ''}</td>
</tr>
"""
        )

    table_rows = "\n".join(rows) if rows else '<tr><td colspan="14">No Module 133 daily report packs found.</td></tr>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HQE Forward Paper History Index</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #0f172a; color: #e5e7eb; }}
header {{ padding: 24px; background: #111827; border-bottom: 1px solid #374151; }}
main {{ padding: 24px; }}
.cards {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }}
.card {{ background: #1f2937; border: 1px solid #374151; border-radius: 12px; padding: 14px; }}
.label {{ color: #9ca3af; font-size: 12px; }}
.value {{ font-size: 20px; font-weight: bold; margin-top: 6px; }}
.table-wrap {{ background: #1f2937; border: 1px solid #374151; border-radius: 12px; overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; min-width: 1200px; }}
th, td {{ padding: 10px 8px; border-bottom: 1px solid #374151; text-align: left; vertical-align: top; }}
th {{ color: #9ca3af; font-weight: normal; background: rgba(255,255,255,0.03); }}
a {{ color: #38bdf8; text-decoration: none; }}
.footer {{ padding: 20px 24px; color: #9ca3af; border-top: 1px solid #374151; }}
</style>
</head>
<body>
<header>
  <h1>HQE Forward Paper History Index</h1>
  <p>Module {MODULE_ID} - {esc(MODULE_NAME)} | Created: {esc(model['created_at'])}</p>
</header>
<main>
  <section class="cards">
    <div class="card"><div class="label">History status</div><div class="value">{esc(model['history_status'])}</div></div>
    <div class="card"><div class="label">Records</div><div class="value">{esc(model['total_records'])}</div></div>
    <div class="card"><div class="label">Signal days</div><div class="value">{esc(summary['signal_days'])}</div></div>
    <div class="card"><div class="label">Open positions est.</div><div class="value">{esc(summary['open_positions_estimated'])}</div></div>
    <div class="card"><div class="label">Total paper PnL</div><div class="value">{esc(summary['total_paper_pnl'])}</div></div>
  </section>
  <section class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th><th>Modified</th><th>Day</th><th>Status</th><th>Signal</th><th>Event</th><th>Action</th>
          <th>Position</th><th>Opened</th><th>Closed</th><th>Paper PnL</th><th>Report</th><th>JSON</th><th>Dashboard</th>
        </tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </section>
</main>
<div class="footer">
  Paper/simulation only. Read-only local index. No broker execution. No real orders. No auto trading. This is not a profitability claim.
</div>
</body>
</html>
"""


def write_history_files(out_dir: Path, model: dict[str, Any]) -> dict[str, str]:
    assert_safety_contract()
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "MODULE_136_DASHBOARD_HISTORY_INDEX_MODEL.json"
    html_path = out_dir / "MODULE_136_DASHBOARD_HISTORY_INDEX.html"
    csv_path = out_dir / "MODULE_136_DASHBOARD_HISTORY_INDEX.csv"
    open_bat = out_dir / "OPEN_MODULE_136_DASHBOARD_HISTORY_INDEX.bat"

    json_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(render_history_html(model), encoding="utf-8")

    fields = [
        "modified_at",
        "day_label",
        "day_status",
        "signal_generated",
        "event",
        "action",
        "gate",
        "position_state",
        "ledger_evaluator_status",
        "entry",
        "stop_loss",
        "target",
        "exit_reason",
        "paper_pnl",
        "opened_positions",
        "closed_positions",
        "open_positions_estimated",
        "total_paper_pnl",
        "daily_pack_json",
        "daily_report_md",
        "dashboard_html",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(model["records"])

    open_bat.write_text(
        "@echo off\n"
        "setlocal\n"
        f'start "" "{html_path}"\n'
        "endlocal\n",
        encoding="utf-8",
    )

    return {
        "history_model_json": str(json_path),
        "history_index_html": str(html_path),
        "history_index_csv": str(csv_path),
        "open_history_index_bat": str(open_bat),
    }


def default_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_136_DASHBOARD_HISTORY_INDEX_{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--runs-root", type=Path, default=Path("D:/HQE_BACKTEST_RUNS"))
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--max-items", type=int, default=50)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = args.out_dir or default_out_dir()
    inputs = HistoryInputs(runs_root=args.runs_root, out_dir=out_dir, max_items=args.max_items)
    model = build_history_model(inputs)
    files = write_history_files(out_dir, model)
    result = {**model, **files, "out_dir": str(out_dir)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
