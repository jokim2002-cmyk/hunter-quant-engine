"""
Module 134: Forward Paper UI Dashboard

Builds a local static HTML dashboard from forward paper-only evidence.

Safety contract:
- Paper/simulation only
- Read-only dashboard
- No broker execution
- No real orders
- No real money approval
- No auto trading
- No option selling
- No profitability claim
- No server required
- No external API required
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


MODULE_ID = 134
MODULE_NAME = "Forward Paper UI Dashboard"

PAPER_ONLY = True
READ_ONLY_DASHBOARD = True
LOCAL_STATIC_HTML_ONLY = True
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
REAL_MONEY_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False
EXTERNAL_API_ALLOWED = False
PROFITABILITY_CLAIM = False

LOCKED_CANDIDATE = "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120"


@dataclass(frozen=True)
class DashboardInputs:
    day_label: str
    daily_pack_json: Path | None
    daily_summary_csv: Path | None
    evidence_manifest_csv: Path | None
    supervisor_summary_json: Path | None
    overlay_json: Path | None
    out_dir: Path


def assert_safety_contract() -> None:
    if not PAPER_ONLY:
        raise RuntimeError("SAFETY_FAIL: PAPER_ONLY must stay True.")
    if not READ_ONLY_DASHBOARD:
        raise RuntimeError("SAFETY_FAIL: dashboard must stay read-only.")
    if not LOCAL_STATIC_HTML_ONLY:
        raise RuntimeError("SAFETY_FAIL: dashboard must stay local static HTML only.")
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


def read_csv_rows(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def pick(*values: Any, default: Any = "") -> Any:
    for value in values:
        if value is not None and str(value).strip() != "":
            return value
    return default


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1", "y"}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if text == "":
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def latest_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return rows[-1] if rows else {}


def dashboard_status(day_status: str, gate: str, evaluator: str) -> str:
    normalized_day_status = str(day_status or "").strip().upper()
    normalized_gate = str(gate or "").strip().upper()
    normalized_evaluator = str(evaluator or "").strip().upper()

    if (
        not normalized_gate
        and not normalized_evaluator
        and (not normalized_day_status or normalized_day_status == "NO_DATA_LOADED")
    ):
        return "NO_DATA_LOADED"

    text = f"{normalized_day_status} {normalized_gate} {normalized_evaluator}".upper()
    if "KILL" in text or "STOP" in text:
        return "STOP_REVIEW_REQUIRED_PAPER_ONLY"
    if "HOLD_MORE_DATA" in text:
        return "HOLD_MORE_DATA_REQUIRED"
    if "REVIEW" in text or "REACHED" in text:
        return "FORWARD_REVIEW_REQUIRED"
    return "PAPER_VALIDATION_CONTINUE"


def build_dashboard_model(inputs: DashboardInputs) -> dict[str, Any]:
    assert_safety_contract()

    daily_pack = read_json(inputs.daily_pack_json)
    supervisor = read_json(inputs.supervisor_summary_json)
    overlay = read_json(inputs.overlay_json)
    summary_rows = read_csv_rows(inputs.daily_summary_csv)
    manifest_rows = read_csv_rows(inputs.evidence_manifest_csv)
    latest_summary = latest_row(summary_rows)

    ledger_stats = daily_pack.get("ledger_stats", {})
    if not isinstance(ledger_stats, dict):
        ledger_stats = {}

    evidence_counts = daily_pack.get("evidence_counts", {})
    if not isinstance(evidence_counts, dict):
        evidence_counts = {}

    day_status = str(pick(daily_pack.get("day_status"), latest_summary.get("day_status"), default="NO_DATA_LOADED"))
    gate = str(pick(daily_pack.get("gate"), overlay.get("gate"), latest_summary.get("gate"), default=""))
    evaluator = str(pick(daily_pack.get("ledger_evaluator_status"), supervisor.get("ledger_evaluator_status"), default=""))

    model = {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "day_label": inputs.day_label,
        "paper_only": True,
        "read_only_dashboard": True,
        "local_static_html_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "external_api_allowed": False,
        "profitability_claim": False,
        "dashboard_status": dashboard_status(day_status, gate, evaluator),
        "day_status": day_status,
        "locked_candidate": str(pick(daily_pack.get("locked_candidate"), supervisor.get("locked_candidate"), overlay.get("locked_candidate"), default=LOCKED_CANDIDATE)),
        "signal_generated": safe_bool(pick(daily_pack.get("signal_generated"), supervisor.get("signal_generated"), overlay.get("signal_generated"), latest_summary.get("signal_generated"), default=False)),
        "event": str(pick(daily_pack.get("event"), supervisor.get("event"), overlay.get("event"), latest_summary.get("event"), default="")),
        "action": str(pick(daily_pack.get("action"), overlay.get("action"), latest_summary.get("action"), default="")),
        "gate": gate,
        "pe_reason": str(pick(daily_pack.get("pe_reason"), supervisor.get("pe_reason"), overlay.get("pe_reason"), default="")),
        "entry": pick(daily_pack.get("entry"), supervisor.get("entry"), overlay.get("entry"), latest_summary.get("entry"), default=""),
        "stop_loss": pick(daily_pack.get("stop_loss"), supervisor.get("stop_loss"), overlay.get("stop_loss"), latest_summary.get("stop_loss"), default=""),
        "target": pick(daily_pack.get("target"), supervisor.get("target"), overlay.get("target"), latest_summary.get("target"), default=""),
        "exit_reason": pick(daily_pack.get("exit_reason"), supervisor.get("exit_reason"), overlay.get("exit_reason"), latest_summary.get("exit_reason"), default=""),
        "paper_pnl": safe_float(pick(daily_pack.get("paper_pnl"), supervisor.get("paper_pnl"), overlay.get("paper_pnl"), latest_summary.get("paper_pnl"), default=0.0)),
        "position_state": str(pick(daily_pack.get("position_state"), supervisor.get("position_state"), overlay.get("position_state"), latest_summary.get("position_state"), default="UNKNOWN")),
        "ledger_evaluator_status": evaluator,
        "plain_hinglish_reason": str(pick(daily_pack.get("plain_hinglish_reason"), overlay.get("plain_hinglish_reason"), default="")),
        "operator_message": str(pick(daily_pack.get("operator_message"), overlay.get("operator_message"), default="")),
        "ledger_stats": {
            "opened_positions": int(safe_float(ledger_stats.get("opened_positions"), 0)),
            "closed_positions": int(safe_float(ledger_stats.get("closed_positions"), 0)),
            "open_positions_estimated": int(safe_float(ledger_stats.get("open_positions_estimated"), 0)),
            "wins": int(safe_float(ledger_stats.get("wins"), 0)),
            "losses": int(safe_float(ledger_stats.get("losses"), 0)),
            "flats": int(safe_float(ledger_stats.get("flats"), 0)),
            "total_paper_pnl": safe_float(ledger_stats.get("total_paper_pnl"), 0.0),
            "average_closed_trade_paper_pnl": safe_float(ledger_stats.get("average_closed_trade_paper_pnl"), 0.0),
        },
        "evidence_counts": {
            "reason_log_rows": int(safe_float(evidence_counts.get("reason_log_rows"), 0)),
            "ledger_rows": int(safe_float(evidence_counts.get("ledger_rows"), 0)),
            "overlay_audit_rows": int(safe_float(evidence_counts.get("overlay_audit_rows"), 0)),
            "manifest_rows": len(manifest_rows),
        },
        "source_files": {
            "daily_pack_json": "" if inputs.daily_pack_json is None else str(inputs.daily_pack_json),
            "daily_summary_csv": "" if inputs.daily_summary_csv is None else str(inputs.daily_summary_csv),
            "evidence_manifest_csv": "" if inputs.evidence_manifest_csv is None else str(inputs.evidence_manifest_csv),
            "supervisor_summary_json": "" if inputs.supervisor_summary_json is None else str(inputs.supervisor_summary_json),
            "overlay_json": "" if inputs.overlay_json is None else str(inputs.overlay_json),
        },
    }
    return model


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def card(title: str, body: str) -> str:
    return f'<section class="card"><h2>{esc(title)}</h2>{body}</section>'


def row(label: str, value: Any) -> str:
    return f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>"


def render_dashboard_html(model: dict[str, Any]) -> str:
    stats = model["ledger_stats"]
    evidence = model["evidence_counts"]
    sources = model["source_files"]

    status_class = "status-hold"
    if "STOP" in model["dashboard_status"]:
        status_class = "status-stop"
    elif "CONTINUE" in model["dashboard_status"] or "REVIEW" in model["dashboard_status"]:
        status_class = "status-ok"

    safety_body = """
<table>
<tr><th>Paper/simulation only</th><td>YES</td></tr>
<tr><th>Read-only dashboard</th><td>YES</td></tr>
<tr><th>Local static HTML only</th><td>YES</td></tr>
<tr><th>Broker execution</th><td>NO</td></tr>
<tr><th>Real orders</th><td>NO</td></tr>
<tr><th>Real money approval</th><td>NO</td></tr>
<tr><th>Auto trading</th><td>NO</td></tr>
<tr><th>Option selling</th><td>NO</td></tr>
<tr><th>External API</th><td>NO</td></tr>
<tr><th>Profitability claim</th><td>NO</td></tr>
</table>
"""

    summary_body = "<table>" + "".join(
        [
            row("Day label", model["day_label"]),
            row("Dashboard status", model["dashboard_status"]),
            row("Day status", model["day_status"]),
            row("Locked candidate", model["locked_candidate"]),
            row("Signal generated", model["signal_generated"]),
            row("Event", model["event"]),
            row("Action", model["action"]),
            row("Gate", model["gate"]),
            row("Position state", model["position_state"]),
            row("Ledger/evaluator status", model["ledger_evaluator_status"]),
        ]
    ) + "</table>"

    trade_body = "<table>" + "".join(
        [
            row("PE reason", model["pe_reason"]),
            row("Entry", model["entry"]),
            row("SL", model["stop_loss"]),
            row("Target", model["target"]),
            row("Exit reason", model["exit_reason"]),
            row("Paper PnL", model["paper_pnl"]),
        ]
    ) + "</table>"

    ledger_body = "<table>" + "".join(
        [
            row("Opened positions", stats["opened_positions"]),
            row("Closed positions", stats["closed_positions"]),
            row("Estimated open positions", stats["open_positions_estimated"]),
            row("Wins", stats["wins"]),
            row("Losses", stats["losses"]),
            row("Flats", stats["flats"]),
            row("Total paper PnL", stats["total_paper_pnl"]),
            row("Average closed trade paper PnL", stats["average_closed_trade_paper_pnl"]),
        ]
    ) + "</table>"

    evidence_body = "<table>" + "".join(
        [
            row("Reason log rows", evidence["reason_log_rows"]),
            row("Ledger rows", evidence["ledger_rows"]),
            row("Overlay audit rows", evidence["overlay_audit_rows"]),
            row("Manifest rows", evidence["manifest_rows"]),
        ]
    ) + "</table>"

    source_rows = "".join(row(name, path) for name, path in sources.items())
    source_body = f"<table>{source_rows}</table>"

    reason_body = f"<p>{esc(model.get('plain_hinglish_reason') or 'No reason available.')}</p>"
    operator_body = f"<p>{esc(model.get('operator_message') or 'No operator message available.')}</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HQE Forward Paper Dashboard - {esc(model['day_label'])}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --bg: #0f172a;
  --panel: #111827;
  --card: #1f2937;
  --text: #e5e7eb;
  --muted: #9ca3af;
  --line: #374151;
  --ok: #22c55e;
  --hold: #f59e0b;
  --stop: #ef4444;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  background: var(--bg);
  color: var(--text);
}}
header {{
  padding: 24px;
  background: var(--panel);
  border-bottom: 1px solid var(--line);
}}
h1 {{
  margin: 0 0 8px 0;
  font-size: 26px;
}}
.subtitle {{
  color: var(--muted);
  margin: 0;
}}
.status {{
  display: inline-block;
  margin-top: 14px;
  padding: 8px 12px;
  border-radius: 999px;
  font-weight: bold;
}}
.status-ok {{ background: rgba(34, 197, 94, 0.18); color: var(--ok); }}
.status-hold {{ background: rgba(245, 158, 11, 0.18); color: var(--hold); }}
.status-stop {{ background: rgba(239, 68, 68, 0.18); color: var(--stop); }}
main {{
  padding: 24px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}}
.card {{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px;
  overflow-wrap: anywhere;
}}
.card.wide {{
  grid-column: 1 / -1;
}}
h2 {{
  margin: 0 0 12px 0;
  font-size: 18px;
}}
table {{
  width: 100%;
  border-collapse: collapse;
}}
th, td {{
  text-align: left;
  padding: 8px 6px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}}
th {{
  width: 38%;
  color: var(--muted);
  font-weight: normal;
}}
.footer {{
  padding: 20px 24px;
  color: var(--muted);
  border-top: 1px solid var(--line);
}}
@media (max-width: 900px) {{
  main {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<header>
  <h1>HQE Forward Paper Dashboard</h1>
  <p class="subtitle">Module {MODULE_ID} - {esc(MODULE_NAME)} | Created: {esc(model['created_at'])}</p>
  <div class="status {status_class}">{esc(model['dashboard_status'])}</div>
</header>
<main>
  {card("Safety", safety_body)}
  {card("Day Summary", summary_body)}
  {card("Trade Plan / Result", trade_body)}
  {card("Ledger Stats", ledger_body)}
  {card("Evidence Counts", evidence_body)}
  {card("Operator Message", operator_body)}
  <section class="card wide"><h2>Plain Hinglish Reason</h2>{reason_body}</section>
  <section class="card wide"><h2>Source Files</h2>{source_body}</section>
</main>
<div class="footer">
  This dashboard is read-only forward paper evidence. It is not a profitability claim and not a real-money approval.
</div>
</body>
</html>
"""


def write_dashboard_files(out_dir: Path, model: dict[str, Any]) -> dict[str, str]:
    assert_safety_contract()
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "MODULE_134_FORWARD_PAPER_DASHBOARD_MODEL.json"
    html_path = out_dir / "MODULE_134_FORWARD_PAPER_DASHBOARD.html"
    summary_csv = out_dir / "MODULE_134_FORWARD_PAPER_DASHBOARD_SUMMARY.csv"
    launcher_bat = out_dir / "OPEN_MODULE_134_FORWARD_PAPER_DASHBOARD.bat"

    json_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(render_dashboard_html(model), encoding="utf-8")

    fields = [
        "created_at",
        "day_label",
        "dashboard_status",
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
        "ledger_evaluator_status",
        "paper_only",
        "read_only_dashboard",
        "broker_execution_allowed",
        "real_orders_allowed",
        "auto_trading_allowed",
        "real_money_allowed",
    ]
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerow(model)

    launcher_bat.write_text(
        "@echo off\n"
        "setlocal\n"
        f'start "" "{html_path}"\n'
        "endlocal\n",
        encoding="utf-8",
    )

    return {
        "dashboard_model_json": str(json_path),
        "dashboard_html": str(html_path),
        "dashboard_summary_csv": str(summary_csv),
        "open_dashboard_bat": str(launcher_bat),
    }


def default_out_dir(day_label: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_day = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in day_label)
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_134_FORWARD_PAPER_UI_DASHBOARD_{safe_day}_{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--day-label", default="FORWARD_PAPER_DAY")
    parser.add_argument("--daily-pack-json", type=Path, default=None)
    parser.add_argument("--daily-summary-csv", type=Path, default=None)
    parser.add_argument("--evidence-manifest-csv", type=Path, default=None)
    parser.add_argument("--supervisor-summary-json", type=Path, default=None)
    parser.add_argument("--overlay-json", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = args.out_dir or default_out_dir(args.day_label)
    inputs = DashboardInputs(
        day_label=args.day_label,
        daily_pack_json=args.daily_pack_json,
        daily_summary_csv=args.daily_summary_csv,
        evidence_manifest_csv=args.evidence_manifest_csv,
        supervisor_summary_json=args.supervisor_summary_json,
        overlay_json=args.overlay_json,
        out_dir=out_dir,
    )
    model = build_dashboard_model(inputs)
    files = write_dashboard_files(out_dir, model)
    result = {**model, **files, "out_dir": str(out_dir)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

