
"""
Module 137: Dashboard Polish / Status Cards / Operator-Friendly Layout

Builds a polished local static operator console from Module 136 history index
or Module 133 daily report packs.

Safety:
- Paper/simulation only
- Read-only operator console
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
import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


MODULE_ID = 137
MODULE_NAME = "Dashboard Polish / Status Cards / Operator-Friendly Layout"

PAPER_ONLY = True
READ_ONLY_OPERATOR_CONSOLE = True
LOCAL_STATIC_HTML_ONLY = True
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
REAL_MONEY_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False
EXTERNAL_API_ALLOWED = False
PROFITABILITY_CLAIM = False

HISTORY_MODEL_NAME = "MODULE_136_DASHBOARD_HISTORY_INDEX_MODEL.json"
DAILY_PACK_NAME = "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"


@dataclass(frozen=True)
class OperatorConsoleInputs:
    runs_root: Path
    out_dir: Path
    history_model_json: Path | None = None
    max_items: int = 10


def assert_safety_contract() -> None:
    if not PAPER_ONLY:
        raise RuntimeError("SAFETY_FAIL: PAPER_ONLY must stay True.")
    if not READ_ONLY_OPERATOR_CONSOLE:
        raise RuntimeError("SAFETY_FAIL: operator console must stay read-only.")
    if not LOCAL_STATIC_HTML_ONLY:
        raise RuntimeError("SAFETY_FAIL: operator console must stay local static HTML only.")

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


def discover_latest_history_model(runs_root: Path) -> Path | None:
    if not runs_root.exists() or not runs_root.is_dir():
        return None
    matches = [path for path in runs_root.rglob(HISTORY_MODEL_NAME) if path.is_file()]
    if not matches:
        return None
    return sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)[0]


def discover_daily_pack_records(runs_root: Path, max_items: int) -> list[dict[str, Any]]:
    if not runs_root.exists() or not runs_root.is_dir():
        return []
    paths = [path for path in runs_root.rglob(DAILY_PACK_NAME) if path.is_file()]
    paths = sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)[: max(1, int(max_items))]
    records: list[dict[str, Any]] = []
    for path in paths:
        pack = read_json(path)
        ledger_stats = pack.get("ledger_stats", {})
        if not isinstance(ledger_stats, dict):
            ledger_stats = {}
        records.append(
            {
                "folder": str(path.parent),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "day_label": str(pick(pack.get("day_label"), path.parent.name, default="UNKNOWN_DAY")),
                "day_status": str(pick(pack.get("day_status"), default="UNKNOWN")),
                "signal_generated": safe_bool(pack.get("signal_generated", False)),
                "event": str(pick(pack.get("event"), default="")),
                "action": str(pick(pack.get("action"), default="")),
                "gate": str(pick(pack.get("gate"), default="")),
                "position_state": str(pick(pack.get("position_state"), default="UNKNOWN")),
                "ledger_evaluator_status": str(pick(pack.get("ledger_evaluator_status"), default="")),
                "paper_pnl": safe_float(pack.get("paper_pnl"), 0.0),
                "opened_positions": int(safe_float(ledger_stats.get("opened_positions"), 0)),
                "closed_positions": int(safe_float(ledger_stats.get("closed_positions"), 0)),
                "open_positions_estimated": int(safe_float(ledger_stats.get("open_positions_estimated"), 0)),
                "total_paper_pnl": safe_float(ledger_stats.get("total_paper_pnl"), 0.0),
                "daily_pack_json": str(path),
            }
        )
    return records


def normalize_history_model(history: dict[str, Any]) -> dict[str, Any]:
    records = history.get("records", [])
    if not isinstance(records, list):
        records = []
    summary = history.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    return {
        "history_status": str(history.get("history_status", "NO_DAILY_PACKS_FOUND")),
        "records": records,
        "summary": {
            "signal_days": int(safe_float(summary.get("signal_days"), 0)),
            "no_signal_days": int(safe_float(summary.get("no_signal_days"), 0)),
            "open_positions_estimated": int(safe_float(summary.get("open_positions_estimated"), 0)),
            "closed_positions": int(safe_float(summary.get("closed_positions"), 0)),
            "total_paper_pnl": safe_float(summary.get("total_paper_pnl"), 0.0),
        },
    }


def build_summary_from_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    signal_days = len([record for record in records if safe_bool(record.get("signal_generated"))])
    no_signal_days = len(records) - signal_days
    return {
        "signal_days": signal_days,
        "no_signal_days": no_signal_days,
        "open_positions_estimated": sum(int(safe_float(record.get("open_positions_estimated"), 0)) for record in records),
        "closed_positions": sum(int(safe_float(record.get("closed_positions"), 0)) for record in records),
        "total_paper_pnl": round(sum(safe_float(record.get("total_paper_pnl"), 0.0) for record in records), 2),
    }


def classify_operator_status(records: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    text = " ".join(
        str(record.get("day_status", "")) + " " + str(record.get("gate", "")) + " " + str(record.get("ledger_evaluator_status", ""))
        for record in records
    ).upper()

    if not records:
        return "NO_DATA_LOADED"
    if "KILL" in text or "STOP" in text:
        return "STOP_REVIEW_REQUIRED_PAPER_ONLY"
    if int(safe_float(summary.get("open_positions_estimated"), 0)) > 0:
        return "OPEN_PAPER_POSITION_MONITOR"
    if "HOLD_MORE_DATA" in text:
        return "HOLD_MORE_DATA_REQUIRED"
    if "REVIEW" in text or "REACHED" in text:
        return "FORWARD_REVIEW_REQUIRED"
    return "PAPER_VALIDATION_CONTINUE"


def operator_message(status: str, latest: dict[str, Any] | None) -> str:
    if status == "NO_DATA_LOADED":
        return "No report pack loaded. Pehle Module 133 daily pack ya Module 136 history index generate karo."
    if status == "STOP_REVIEW_REQUIRED_PAPER_ONLY":
        return "STOP. Paper evidence me risk/kill condition dikhi. Manual review required. Real money still NO."
    if status == "OPEN_PAPER_POSITION_MONITOR":
        return "Open paper position monitor karo. Ye simulated hai; real order ya broker action allowed nahi."
    if status == "HOLD_MORE_DATA_REQUIRED":
        return "Forward validation me abhi more data required hai. Continue paper logging only."
    if status == "FORWARD_REVIEW_REQUIRED":
        return "Forward review threshold reached. Manual review karo; real money approval automatic nahi hai."
    return "Paper validation continue. Koi real-market action allowed nahi."


def build_operator_console_model(inputs: OperatorConsoleInputs) -> dict[str, Any]:
    assert_safety_contract()

    history_path = inputs.history_model_json or discover_latest_history_model(inputs.runs_root)
    source_mode = "HISTORY_MODEL"
    history = read_json(history_path)

    if history:
        normalized = normalize_history_model(history)
        records = normalized["records"][: max(1, int(inputs.max_items))]
        summary = normalized["summary"]
    else:
        source_mode = "DAILY_PACK_DISCOVERY"
        records = discover_daily_pack_records(inputs.runs_root, inputs.max_items)
        summary = build_summary_from_records(records)

    latest = records[0] if records else None
    status = classify_operator_status(records, summary)

    model = {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "paper_only": True,
        "read_only_operator_console": True,
        "local_static_html_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "external_api_allowed": False,
        "profitability_claim": False,
        "runs_root": str(inputs.runs_root),
        "history_model_json": "" if history_path is None else str(history_path),
        "source_mode": source_mode,
        "operator_status": status,
        "operator_message": operator_message(status, latest),
        "latest_day_label": "" if latest is None else str(latest.get("day_label", "")),
        "latest_day_status": "" if latest is None else str(latest.get("day_status", "")),
        "latest_event": "" if latest is None else str(latest.get("event", "")),
        "latest_action": "" if latest is None else str(latest.get("action", "")),
        "latest_position_state": "" if latest is None else str(latest.get("position_state", "")),
        "total_records": len(records),
        "summary": summary,
        "records": records,
    }
    return model


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def status_class(status: str) -> str:
    upper = status.upper()
    if "STOP" in upper:
        return "stop"
    if "OPEN" in upper:
        return "open"
    if "HOLD" in upper:
        return "hold"
    if "REVIEW" in upper:
        return "review"
    return "ok"


def render_operator_console_html(model: dict[str, Any]) -> str:
    summary = model["summary"]
    records = model["records"]
    rows: list[str] = []

    for index, record in enumerate(records, start=1):
        rows.append(
            f"""
<tr>
  <td>{index}</td>
  <td>{esc(record.get('day_label', ''))}</td>
  <td>{esc(record.get('day_status', ''))}</td>
  <td>{esc(record.get('signal_generated', ''))}</td>
  <td>{esc(record.get('event', ''))}</td>
  <td>{esc(record.get('action', ''))}</td>
  <td>{esc(record.get('position_state', ''))}</td>
  <td>{esc(record.get('opened_positions', ''))}</td>
  <td>{esc(record.get('closed_positions', ''))}</td>
  <td>{esc(record.get('total_paper_pnl', ''))}</td>
</tr>
"""
        )

    table_rows = "\n".join(rows) if rows else '<tr><td colspan="10">No paper history loaded.</td></tr>'

    klass = status_class(str(model["operator_status"]))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HQE Operator Console</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #0b1120; color: #e5e7eb; }}
header {{ padding: 24px; background: #111827; border-bottom: 1px solid #334155; }}
h1 {{ margin: 0 0 8px 0; }}
main {{ padding: 24px; }}
.banner {{ border-radius: 16px; padding: 20px; margin-bottom: 18px; border: 1px solid #334155; }}
.banner.ok {{ background: rgba(34,197,94,0.12); }}
.banner.hold {{ background: rgba(245,158,11,0.13); }}
.banner.open {{ background: rgba(59,130,246,0.14); }}
.banner.review {{ background: rgba(168,85,247,0.14); }}
.banner.stop {{ background: rgba(239,68,68,0.15); }}
.status {{ font-size: 28px; font-weight: 800; margin-bottom: 8px; }}
.message {{ color: #cbd5e1; font-size: 16px; }}
.cards {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }}
.card {{ background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 16px; }}
.label {{ color: #94a3b8; font-size: 12px; }}
.value {{ font-size: 22px; font-weight: 800; margin-top: 7px; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; }}
.panel {{ background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 16px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px 8px; border-bottom: 1px solid #334155; text-align: left; vertical-align: top; }}
th {{ color: #94a3b8; font-weight: normal; }}
.footer {{ padding: 20px 24px; color: #94a3b8; border-top: 1px solid #334155; }}
@media (max-width: 900px) {{
  .cards {{ grid-template-columns: 1fr 1fr; }}
  .grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<header>
  <h1>HQE Forward Paper Operator Console</h1>
  <p>Module {MODULE_ID} - {esc(MODULE_NAME)} | Created: {esc(model['created_at'])}</p>
</header>
<main>
  <section class="banner {klass}">
    <div class="status">{esc(model['operator_status'])}</div>
    <div class="message">{esc(model['operator_message'])}</div>
  </section>

  <section class="cards">
    <div class="card"><div class="label">Records</div><div class="value">{esc(model['total_records'])}</div></div>
    <div class="card"><div class="label">Signal days</div><div class="value">{esc(summary.get('signal_days', 0))}</div></div>
    <div class="card"><div class="label">No-signal days</div><div class="value">{esc(summary.get('no_signal_days', 0))}</div></div>
    <div class="card"><div class="label">Open positions est.</div><div class="value">{esc(summary.get('open_positions_estimated', 0))}</div></div>
    <div class="card"><div class="label">Total paper PnL</div><div class="value">{esc(summary.get('total_paper_pnl', 0))}</div></div>
  </section>

  <section class="grid">
    <div class="panel">
      <h2>Latest Day</h2>
      <table>
        <tr><th>Day</th><td>{esc(model['latest_day_label'])}</td></tr>
        <tr><th>Status</th><td>{esc(model['latest_day_status'])}</td></tr>
        <tr><th>Event</th><td>{esc(model['latest_event'])}</td></tr>
        <tr><th>Action</th><td>{esc(model['latest_action'])}</td></tr>
        <tr><th>Position</th><td>{esc(model['latest_position_state'])}</td></tr>
      </table>
    </div>
    <div class="panel">
      <h2>Safety Lock</h2>
      <table>
        <tr><th>Paper/simulation only</th><td>YES</td></tr>
        <tr><th>Read-only console</th><td>YES</td></tr>
        <tr><th>Broker execution</th><td>NO</td></tr>
        <tr><th>Real orders</th><td>NO</td></tr>
        <tr><th>Auto trading</th><td>NO</td></tr>
        <tr><th>Profitability claim</th><td>NO</td></tr>
      </table>
    </div>
  </section>

  <section class="panel">
    <h2>Recent Paper Days</h2>
    <table>
      <thead>
        <tr>
          <th>#</th><th>Day</th><th>Status</th><th>Signal</th><th>Event</th><th>Action</th>
          <th>Position</th><th>Opened</th><th>Closed</th><th>Paper PnL</th>
        </tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </section>
</main>
<div class="footer">
  Paper-only operator console. No broker execution. No real orders. No auto trading. This is not a profitability claim.
</div>
</body>
</html>
"""


def write_operator_console_files(out_dir: Path, model: dict[str, Any]) -> dict[str, str]:
    assert_safety_contract()
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / "MODULE_137_OPERATOR_CONSOLE_MODEL.json"
    html_path = out_dir / "MODULE_137_OPERATOR_CONSOLE.html"
    open_bat = out_dir / "OPEN_MODULE_137_OPERATOR_CONSOLE.bat"

    model_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(render_operator_console_html(model), encoding="utf-8")
    open_bat.write_text(
        "@echo off\n"
        "setlocal\n"
        f'start "" "{html_path}"\n'
        "endlocal\n",
        encoding="utf-8",
    )

    return {
        "operator_console_model_json": str(model_path),
        "operator_console_html": str(html_path),
        "open_operator_console_bat": str(open_bat),
    }


def default_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_137_OPERATOR_CONSOLE_{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--runs-root", type=Path, default=Path("D:/HQE_BACKTEST_RUNS"))
    parser.add_argument("--history-model-json", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--max-items", type=int, default=10)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = args.out_dir or default_out_dir()
    inputs = OperatorConsoleInputs(
        runs_root=args.runs_root,
        out_dir=out_dir,
        history_model_json=args.history_model_json,
        max_items=args.max_items,
    )
    model = build_operator_console_model(inputs)
    files = write_operator_console_files(out_dir, model)
    result = {**model, **files, "out_dir": str(out_dir)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
