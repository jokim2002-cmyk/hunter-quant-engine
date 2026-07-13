from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hqe_app_daily_operations import (
    resolve_latest_evidence,
    resolve_latest_report,
)


STATUS_COPY = {
    "NO_COMPLETED_TRADES_HOLD_MORE_DATA_REQUIRED": {
        "headline": "NO PAPER TRADE TODAY",
        "badge": "MORE VALIDATION DAYS REQUIRED",
        "meaning": (
            "Aaj koi completed paper trade nahi hua. Valid signal aur entry "
            "record nahi mili, isliye HQE ne safe HOLD decision liya. "
            "Validation continue karne ke liye aur genuine market days chahiye."
        ),
    },
    "NO_TRADE": {
        "headline": "NO PAPER TRADE TODAY",
        "badge": "VALID NO-TRADE DAY",
        "meaning": (
            "Aaj strategy conditions complete nahi hui, isliye paper trade "
            "open nahi hua. Ye loss nahi hai; ye valid no-trade outcome hai."
        ),
    },
    "COMPLETED": {
        "headline": "PAPER SESSION COMPLETED",
        "badge": "SESSION COMPLETE",
        "meaning": (
            "Paper session complete hui. Neeche trade counts, paper P&L aur "
            "exit details review karo."
        ),
    },
}


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file() or path.suffix.lower() != ".json":
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    rendered = str(value).strip()
    return rendered if rendered else fallback


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _money(value: Any) -> str:
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def _yes_no(value: Any) -> str:
    return "Yes" if bool(value) else "No"


def _day_parts(payload: dict[str, Any]) -> tuple[str, str]:
    label = _text(payload.get("day_label"))
    match = re.fullmatch(r"DAY_(\d+)_(\d{4}-\d{2}-\d{2})", label)
    if match:
        number = int(match.group(1))
        raw_date = match.group(2)
        try:
            pretty_date = datetime.strptime(
                raw_date,
                "%Y-%m-%d",
            ).strftime("%d %b %Y")
        except ValueError:
            pretty_date = raw_date
        return f"Day {number:03d}", pretty_date

    created_at = _text(payload.get("created_at"))
    fallback_date = created_at[:10] if len(created_at) >= 10 else "Date unavailable"
    return "Validation day", fallback_date


def _status_copy(payload: dict[str, Any]) -> dict[str, str]:
    raw = _text(payload.get("day_status"), "STATUS_NOT_RECORDED").upper()
    if raw in STATUS_COPY:
        return STATUS_COPY[raw]
    if "NO_COMPLETED_TRADES" in raw:
        return STATUS_COPY["NO_COMPLETED_TRADES_HOLD_MORE_DATA_REQUIRED"]
    if "NO_TRADE" in raw:
        return STATUS_COPY["NO_TRADE"]
    if "COMPLETE" in raw or "PASS" in raw:
        return STATUS_COPY["COMPLETED"]
    return {
        "headline": raw.replace("_", " ").title(),
        "badge": "REVIEW SESSION",
        "meaning": (
            "Session ka internal status available hai. Neeche paper trade "
            "summary aur evidence quality review karo."
        ),
    }


def _strategy_rows(candidate: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = [
        ("Locked candidate", candidate or "Not recorded"),
    ]
    if "SMC_BIDIRECTIONAL" in candidate:
        rows.append(
            (
                "Direction mapping",
                "Bullish SMC -> CE BUY | Bearish SMC -> PE BUY",
            )
        )
    elif "PE_ONLY" in candidate:
        rows.append(("Option side", "PE only"))
    dte = re.search(r"DTE_GE_(\d+)", candidate)
    if dte:
        rows.append(("Minimum DTE", f"{dte.group(1)} day or more"))
    ltp = re.search(r"LTP_(\d+)_(\d+)", candidate)
    if ltp:
        rows.append(
            (
                "Allowed option premium",
                f"₹{ltp.group(1)} to ₹{ltp.group(2)}",
            )
        )
    stop = re.search(r"SL(\d+)", candidate)
    if stop:
        rows.append(("Stop-loss setting", f"{stop.group(1)} (strategy code)"))
    target = re.search(r"TGT(\d+)", candidate)
    if target:
        rows.append(("Target setting", f"{target.group(1)} (strategy code)"))
    return rows


def _trade_value(value: Any, empty_label: str) -> str:
    rendered = _text(value)
    if not rendered or rendered.upper() in {"NOT_AVAILABLE", "UNKNOWN"}:
        return empty_label
    return rendered


def _row(label: str, value: str, tone: str = "") -> str:
    tone_class = f" {tone}" if tone else ""
    return (
        f'<div class="detail-row{tone_class}">'
        f'<span>{html.escape(label)}</span>'
        f'<strong>{html.escape(value)}</strong>'
        "</div>"
    )


def _metric(label: str, value: str, tone: str = "teal") -> str:
    return (
        f'<article class="metric {html.escape(tone)}">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        "</article>"
    )


def _evidence_notes(payload: dict[str, Any]) -> list[str]:
    counts = payload.get("evidence_counts", {})
    if not isinstance(counts, dict):
        counts = {}

    notes: list[str] = []
    ledger_rows = _int(counts.get("ledger_rows"))
    reason_rows = _int(counts.get("reason_log_rows"))
    overlay_rows = _int(counts.get("overlay_audit_rows"))
    supervisor_present = bool(counts.get("supervisor_report_present"))
    overlay_present = bool(counts.get("overlay_report_present"))

    if ledger_rows == 0:
        notes.append(
            "Paper ledger me koi trade row record nahi hui."
        )
    if reason_rows == 0:
        notes.append(
            "Dedicated reason-log row available nahi hai; no-trade explanation "
            "day status se banayi gayi hai."
        )
    if not supervisor_present:
        notes.append("Supervisor summary is Day pack me present nahi hai.")
    if not overlay_present and overlay_rows == 0:
        notes.append("Overlay audit/report is Day pack me present nahi hai.")

    return notes


def _technical_details(
    report_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    same_source: bool,
) -> str:
    blocks: list[str] = []

    if report_payload:
        pretty = json.dumps(
            report_payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        blocks.append(
            "<details>"
            "<summary>Raw daily report JSON</summary>"
            f"<pre>{html.escape(pretty)}</pre>"
            "</details>"
        )

    if evidence_payload and not same_source:
        pretty = json.dumps(
            evidence_payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        blocks.append(
            "<details>"
            "<summary>Raw market-close evidence JSON</summary>"
            f"<pre>{html.escape(pretty)}</pre>"
            "</details>"
        )

    if not blocks:
        return '<p class="muted">Raw JSON source available nahi hai.</p>'
    return "".join(blocks)


def ensure_trader_report(workspace: Path) -> Path | None:
    report_path = resolve_latest_report(workspace)
    evidence_path = resolve_latest_evidence(workspace)

    report_payload = _load_json(report_path)
    evidence_payload = _load_json(evidence_path)

    if not report_payload and evidence_payload:
        report_payload = evidence_payload

    if not report_payload:
        return None

    same_source = bool(
        report_path is not None
        and evidence_path is not None
        and report_path.resolve() == evidence_path.resolve()
    )

    day_name, session_date = _day_parts(report_payload)
    status = _status_copy(report_payload)

    stats = report_payload.get("ledger_stats", {})
    if not isinstance(stats, dict):
        stats = {}

    signal_generated = bool(report_payload.get("signal_generated"))
    opened = _int(stats.get("opened_positions"))
    closed = _int(stats.get("closed_positions"))
    open_estimated = _int(stats.get("open_positions_estimated"))
    wins = _int(stats.get("wins"))
    losses = _int(stats.get("losses"))
    flats = _int(stats.get("flats"))
    paper_pnl = _money(
        stats.get(
            "total_paper_pnl",
            report_payload.get("paper_pnl", 0),
        )
    )

    if signal_generated:
        signal_text = "Generated"
        signal_tone = "green"
    else:
        signal_text = "Not generated"
        signal_tone = "amber"

    if closed > 0:
        position_text = f"{closed} closed"
        position_tone = "green"
    elif opened > 0 or open_estimated > 0:
        position_text = f"{max(opened, open_estimated)} open"
        position_tone = "amber"
    else:
        position_text = "No position"
        position_tone = "teal"

    plain_reason = _text(report_payload.get("plain_hinglish_reason"))
    pe_reason = _text(report_payload.get("pe_reason"))
    if plain_reason:
        no_trade_reason = plain_reason
    elif pe_reason and pe_reason.upper() != "NOT_AVAILABLE":
        no_trade_reason = pe_reason.replace("_", " ").title()
    else:
        no_trade_reason = status["meaning"]

    entry = _trade_value(
        report_payload.get("entry"),
        "Not generated — no signal",
    )
    stop_loss = _trade_value(
        report_payload.get("stop_loss"),
        "Not generated — no entry",
    )
    target = _trade_value(
        report_payload.get("target"),
        "Not generated — no entry",
    )
    exit_reason = _trade_value(
        report_payload.get("exit_reason"),
        "Not applicable",
    )
    action = _trade_value(
        report_payload.get("action"),
        "HOLD / NO ACTION",
    )
    gate = _trade_value(
        report_payload.get("gate"),
        "No entry gate recorded",
    )

    candidate = _text(report_payload.get("locked_candidate"))
    strategy_rows = "".join(
        _row(label, value)
        for label, value in _strategy_rows(candidate)
    )

    evidence_notes = _evidence_notes(report_payload)
    evidence_html = (
        "<ul>"
        + "".join(
            f"<li>{html.escape(note)}</li>"
            for note in evidence_notes
        )
        + "</ul>"
        if evidence_notes
        else "<p>Evidence pack complete dikhta hai.</p>"
    )

    created_at = _text(report_payload.get("created_at"))
    generated_at = datetime.now(timezone.utc).astimezone().strftime(
        "%d %b %Y, %I:%M:%S %p %Z"
    )

    source_names: list[str] = []
    if report_path is not None:
        source_names.append(report_path.name)
    if evidence_path is not None and not same_source:
        source_names.append(evidence_path.name)

    source_text = " · ".join(source_names) or "Source file not recorded"

    metrics = "".join(
        [
            _metric("Signal", signal_text, signal_tone),
            _metric("Paper position", position_text, position_tone),
            _metric("Completed trades", str(closed), "teal"),
            _metric("Paper P&L", paper_pnl, "teal"),
            _metric("Wins", str(wins), "green"),
            _metric("Losses", str(losses), "red" if losses else "teal"),
            _metric("Flat exits", str(flats), "teal"),
            _metric("Real orders", "Blocked", "green"),
        ]
    )

    trade_rows = "".join(
        [
            _row("System action", action, "strong"),
            _row("Entry gate", gate),
            _row("Entry", entry),
            _row("Stop loss", stop_loss),
            _row("Target", target),
            _row("Exit reason", exit_reason),
        ]
    )

    safety_rows = "".join(
        [
            _row(
                "Paper-only mode",
                _yes_no(report_payload.get("paper_only")),
            ),
            _row(
                "Real money allowed",
                _yes_no(report_payload.get("real_money_allowed")),
            ),
            _row(
                "Real orders allowed",
                _yes_no(report_payload.get("real_orders_allowed")),
            ),
            _row(
                "Broker execution allowed",
                _yes_no(
                    report_payload.get("broker_execution_allowed")
                ),
            ),
            _row(
                "Auto trading allowed",
                _yes_no(report_payload.get("auto_trading_allowed")),
            ),
            _row(
                "Option selling allowed",
                _yes_no(report_payload.get("option_selling_allowed")),
            ),
        ]
    )

    technical = _technical_details(
        report_payload,
        evidence_payload,
        same_source,
    )

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HQE Daily Trader Report</title>
<style>
:root {{
  color-scheme: dark;
  --bg:#07111f;
  --panel:#101d31;
  --panel-2:#172841;
  --text:#f8fafc;
  --muted:#a8b8cc;
  --accent:#2dd4bf;
  --green:#22c55e;
  --amber:#f59e0b;
  --red:#ef4444;
  --border:#29415f;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  background:linear-gradient(145deg,#07111f,#0b1728);
  color:var(--text);
  font-family:"Segoe UI",Arial,sans-serif;
}}
main {{
  max-width:1120px;
  margin:0 auto;
  padding:24px;
}}
.hero {{
  border:1px solid var(--accent);
  background:linear-gradient(135deg,#0a2a35,#101d31);
  border-radius:18px;
  padding:26px;
  box-shadow:0 18px 50px rgba(0,0,0,.28);
}}
.brand {{
  color:var(--accent);
  font-size:13px;
  font-weight:800;
  letter-spacing:.13em;
}}
.hero-top {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:20px;
  margin-top:10px;
}}
h1 {{
  margin:0;
  font-size:34px;
  line-height:1.15;
}}
.day {{
  color:var(--muted);
  margin-top:8px;
  font-size:16px;
}}
.badge {{
  flex:0 0 auto;
  padding:10px 14px;
  border:1px solid rgba(245,158,11,.65);
  color:#fbbf24;
  background:rgba(245,158,11,.10);
  border-radius:999px;
  font-weight:800;
  font-size:12px;
}}
.summary {{
  margin:20px 0 0;
  padding:16px 18px;
  background:rgba(0,0,0,.16);
  border-left:4px solid var(--amber);
  border-radius:10px;
  line-height:1.65;
  font-size:16px;
}}
.lock {{
  display:inline-block;
  margin-top:16px;
  color:var(--accent);
  font-size:12px;
  font-weight:800;
}}
.metrics {{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:13px;
  margin:20px 0;
}}
.metric {{
  min-height:108px;
  padding:17px;
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:14px;
  border-left-width:5px;
}}
.metric.teal {{ border-left-color:var(--accent); }}
.metric.green {{ border-left-color:var(--green); }}
.metric.amber {{ border-left-color:var(--amber); }}
.metric.red {{ border-left-color:var(--red); }}
.metric-label {{
  color:var(--muted);
  font-size:13px;
}}
.metric-value {{
  margin-top:10px;
  font-size:22px;
  font-weight:800;
}}
.grid-2 {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:16px;
}}
.panel {{
  margin:16px 0;
  padding:22px;
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:15px;
}}
.panel h2 {{
  margin:0 0 16px;
  font-size:20px;
}}
.reason {{
  font-size:17px;
  line-height:1.7;
  color:#e2e8f0;
}}
.detail-row {{
  display:flex;
  justify-content:space-between;
  gap:18px;
  padding:12px 0;
  border-bottom:1px solid rgba(41,65,95,.68);
}}
.detail-row:last-child {{ border-bottom:0; }}
.detail-row span {{ color:var(--muted); }}
.detail-row strong {{
  text-align:right;
  word-break:break-word;
}}
.detail-row.strong strong {{ color:var(--accent); }}
ul {{
  margin:0;
  padding-left:21px;
}}
li {{
  margin:9px 0;
  line-height:1.55;
}}
.muted {{
  color:var(--muted);
}}
.source {{
  margin-top:14px;
  color:var(--muted);
  font-size:12px;
  word-break:break-all;
}}
details {{
  margin:10px 0;
  background:var(--panel-2);
  border:1px solid var(--border);
  border-radius:10px;
  overflow:hidden;
}}
summary {{
  padding:14px;
  cursor:pointer;
  font-weight:700;
}}
pre {{
  margin:0;
  padding:16px;
  max-height:480px;
  overflow:auto;
  background:#050b14;
  color:#cbd5e1;
  font-size:12px;
  line-height:1.5;
}}
.footer {{
  padding:18px 4px 6px;
  text-align:center;
  color:var(--muted);
  font-size:12px;
}}
@media (max-width:850px) {{
  .metrics {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .grid-2 {{ grid-template-columns:1fr; }}
  .hero-top {{ flex-direction:column; }}
}}
@media (max-width:520px) {{
  main {{ padding:12px; }}
  .metrics {{ grid-template-columns:1fr; }}
  h1 {{ font-size:27px; }}
  .detail-row {{ flex-direction:column; gap:5px; }}
  .detail-row strong {{ text-align:left; }}
}}
</style>
</head>
<body>
<main>
<section class="hero">
  <div class="brand">HUNTER QUANT ENGINE</div>
  <div class="hero-top">
    <div>
      <h1>{html.escape(status["headline"])}</h1>
      <div class="day">
        {html.escape(day_name)} · {html.escape(session_date)}
      </div>
    </div>
    <div class="badge">{html.escape(status["badge"])}</div>
  </div>
  <div class="summary">{html.escape(status["meaning"])}</div>
  <div class="lock">
    PAPER / SIMULATION ONLY · REAL ORDERS BLOCKED
  </div>
</section>

<section class="metrics">{metrics}</section>

<section class="panel">
  <h2>Simple trader summary</h2>
  <p class="reason">{html.escape(no_trade_reason)}</p>
  <div class="detail-row">
    <span>Bottom line</span>
    <strong>
      No signal + no entry + no completed trade = paper P&L ₹0.00
    </strong>
  </div>
</section>

<div class="grid-2">
  <section class="panel">
    <h2>Trade details</h2>
    {trade_rows}
  </section>

  <section class="panel">
    <h2>Strategy setup used</h2>
    {strategy_rows}
  </section>
</div>

<div class="grid-2">
  <section class="panel">
    <h2>Evidence quality</h2>
    {evidence_html}
  </section>

  <section class="panel">
    <h2>Safety confirmation</h2>
    {safety_rows}
  </section>
</div>

<section class="panel">
  <h2>Technical evidence</h2>
  <p class="muted">
    Ye section audit/debugging ke liye hai. Normal trader ko ise padhne ki
    zarurat nahi hai.
  </p>
  {technical}
  <div class="source">
    Source: {html.escape(source_text)}
    {(" · Pack created: " + html.escape(created_at)) if created_at else ""}
  </div>
</section>

<div class="footer">
  Report generated {html.escape(generated_at)} ·
  This is not a profitability claim.
</div>
</main>
</body>
</html>
"""

    output_dir = workspace / "HQE_TRADER_REPORTS"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "HQE_TRADER_REPORT_LATEST.html"
    output_path.write_text(document, encoding="utf-8")
    return output_path
