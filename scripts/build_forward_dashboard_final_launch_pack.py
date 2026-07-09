from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

MODULE_ID = 138
MODULE_NAME = "Dashboard Final Launch Pack / One-Click Open All Dashboards"

PAPER_ONLY = True
READ_ONLY_LAUNCH_PACK = True
LOCAL_STATIC_HTML_ONLY = True
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
REAL_MONEY_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False
EXTERNAL_API_ALLOWED = False
PROFITABILITY_CLAIM = False

ARTIFACT_NAMES = {
    "operator_console_html": "MODULE_137_OPERATOR_CONSOLE.html",
    "operator_console_model_json": "MODULE_137_OPERATOR_CONSOLE_MODEL.json",
    "history_index_html": "MODULE_136_DASHBOARD_HISTORY_INDEX.html",
    "history_model_json": "MODULE_136_DASHBOARD_HISTORY_INDEX_MODEL.json",
    "latest_dashboard_html": "MODULE_134_FORWARD_PAPER_DASHBOARD.html",
    "daily_report_md": "MODULE_133_DAILY_PAPER_TRADING_REPORT.md",
    "daily_pack_json": "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json",
}


@dataclass(frozen=True)
class FinalLaunchInputs:
    runs_root: Path
    out_dir: Path


def assert_safety_contract() -> None:
    if not PAPER_ONLY:
        raise RuntimeError("SAFETY_FAIL: PAPER_ONLY must stay True.")
    if not READ_ONLY_LAUNCH_PACK:
        raise RuntimeError("SAFETY_FAIL: launch pack must stay read-only.")
    if not LOCAL_STATIC_HTML_ONLY:
        raise RuntimeError("SAFETY_FAIL: launch pack must stay local static HTML only.")

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


def safe_read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def latest_file(root: Path, filename: str) -> Path | None:
    if not root.exists() or not root.is_dir():
        return None
    matches: list[Path] = []
    try:
        for path in root.rglob(filename):
            if path.is_file():
                matches.append(path)
    except Exception:
        return None
    if not matches:
        return None
    return sorted(matches, key=lambda item: item.stat().st_mtime, reverse=True)[0]


def artifact_record(root: Path, key: str, filename: str) -> dict[str, Any]:
    path = latest_file(root, filename)
    if path is None:
        return {"key": key, "filename": filename, "present": False, "path": "", "modified_at": ""}
    return {
        "key": key,
        "filename": filename,
        "present": True,
        "path": str(path),
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
    }


def pick(*values: Any, default: Any = "") -> Any:
    for value in values:
        if value is not None and str(value).strip() != "":
            return value
    return default


def build_final_launch_model(inputs: FinalLaunchInputs) -> dict[str, Any]:
    assert_safety_contract()

    artifacts = {key: artifact_record(inputs.runs_root, key, filename) for key, filename in ARTIFACT_NAMES.items()}

    operator_model = safe_read_json(Path(artifacts["operator_console_model_json"]["path"]) if artifacts["operator_console_model_json"]["present"] else None)
    history_model = safe_read_json(Path(artifacts["history_model_json"]["path"]) if artifacts["history_model_json"]["present"] else None)
    daily_pack = safe_read_json(Path(artifacts["daily_pack_json"]["path"]) if artifacts["daily_pack_json"]["present"] else None)

    present_count = len([item for item in artifacts.values() if item["present"]])
    missing_artifacts = [key for key, item in artifacts.items() if not item["present"]]

    if present_count == 0:
        launch_status = "NO_DASHBOARD_ARTIFACTS_FOUND"
    elif missing_artifacts:
        launch_status = "PARTIAL_DASHBOARD_SUITE_READY"
    else:
        launch_status = "READY_TO_OPEN_DASHBOARD_SUITE"

    return {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "paper_only": True,
        "read_only_launch_pack": True,
        "local_static_html_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "external_api_allowed": False,
        "profitability_claim": False,
        "runs_root": str(inputs.runs_root),
        "launch_status": launch_status,
        "present_artifacts": present_count,
        "missing_artifacts": missing_artifacts,
        "operator_status": str(operator_model.get("operator_status", "")),
        "operator_message": str(operator_model.get("operator_message", "")),
        "latest_day_label": str(pick(operator_model.get("latest_day_label"), daily_pack.get("day_label"), default="")),
        "latest_event": str(pick(operator_model.get("latest_event"), daily_pack.get("event"), default="")),
        "latest_action": str(pick(operator_model.get("latest_action"), daily_pack.get("action"), default="")),
        "latest_position_state": str(pick(operator_model.get("latest_position_state"), daily_pack.get("position_state"), default="")),
        "history_status": str(history_model.get("history_status", "")),
        "total_history_records": int(float(history_model.get("total_records", 0) or 0)),
        "artifacts": artifacts,
    }


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def path_link(path_text: str, label: str) -> str:
    if not path_text:
        return '<span class="missing">Missing</span>'
    try:
        href = Path(path_text).resolve().as_uri()
    except Exception:
        href = path_text
    return f'<a href="{esc(href)}">{esc(label)}</a>'


def render_final_launch_html(model: dict[str, Any]) -> str:
    artifacts = model["artifacts"]

    card_items = [
        ("Operator Console", artifacts["operator_console_html"]),
        ("History Index", artifacts["history_index_html"]),
        ("Latest Dashboard", artifacts["latest_dashboard_html"]),
        ("Daily Report", artifacts["daily_report_md"]),
    ]

    cards = ""
    for title, record in card_items:
        status = "READY" if record["present"] else "MISSING"
        cards += f"""
<section class="card">
  <div class="tag">{esc(status)}</div>
  <h2>{esc(title)}</h2>
  <p>{path_link(record["path"], "Open")}</p>
</section>
"""

    rows = ""
    for key, record in artifacts.items():
        rows += f"""
<tr>
  <td>{esc(key)}</td>
  <td>{esc(record["filename"])}</td>
  <td>{esc(record["present"])}</td>
  <td>{esc(record["modified_at"])}</td>
  <td>{path_link(record["path"], "Open")}</td>
</tr>
"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HQE Dashboard Final Launch Pack</title>
<style>
body {{ margin:0; font-family:Arial,Helvetica,sans-serif; background:#07111f; color:#e5e7eb; }}
header {{ padding:24px; background:#111827; border-bottom:1px solid #334155; }}
main {{ padding:24px; }}
.banner,.card,.panel {{ background:#1e293b; border:1px solid #334155; border-radius:14px; padding:18px; margin-bottom:16px; }}
.status {{ font-size:26px; font-weight:800; }}
.cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.tag {{ color:#38bdf8; font-weight:800; }}
a {{ color:#38bdf8; font-weight:700; text-decoration:none; }}
.missing {{ color:#f87171; font-weight:700; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:9px; border-bottom:1px solid #334155; text-align:left; }}
.footer {{ padding:20px 24px; color:#94a3b8; border-top:1px solid #334155; }}
</style>
</head>
<body>
<header>
<h1>HQE Dashboard Final Launch Pack</h1>
<p>Module {MODULE_ID} - {esc(MODULE_NAME)} | Created: {esc(model["created_at"])}</p>
</header>
<main>
<section class="banner">
<div class="status">{esc(model["launch_status"])}</div>
<p>{esc(model.get("operator_message") or "Open all read-only paper dashboards from one place. Real trading remains disabled.")}</p>
</section>

<section class="cards">{cards}</section>

<section class="panel">
<h2>Latest Paper Status</h2>
<table>
<tr><th>Operator status</th><td>{esc(model["operator_status"])}</td></tr>
<tr><th>Latest day</th><td>{esc(model["latest_day_label"])}</td></tr>
<tr><th>Latest event</th><td>{esc(model["latest_event"])}</td></tr>
<tr><th>Latest action</th><td>{esc(model["latest_action"])}</td></tr>
<tr><th>Latest position</th><td>{esc(model["latest_position_state"])}</td></tr>
<tr><th>History status</th><td>{esc(model["history_status"])}</td></tr>
<tr><th>Total history records</th><td>{esc(model["total_history_records"])}</td></tr>
</table>
</section>

<section class="panel">
<h2>Safety Lock</h2>
<table>
<tr><th>Paper/simulation only</th><td>YES</td></tr>
<tr><th>Read-only launch pack</th><td>YES</td></tr>
<tr><th>Local static HTML only</th><td>YES</td></tr>
<tr><th>External API</th><td>NO</td></tr>
<tr><th>Broker execution</th><td>NO</td></tr>
<tr><th>Real orders</th><td>NO</td></tr>
<tr><th>Auto trading</th><td>NO</td></tr>
<tr><th>Profitability claim</th><td>NO</td></tr>
</table>
</section>

<section class="panel">
<h2>Artifact Inventory</h2>
<table>
<thead><tr><th>Key</th><th>Filename</th><th>Present</th><th>Modified</th><th>Open</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</section>
</main>
<div class="footer">Paper-only launch page. No broker execution. No real orders. No auto trading. This is not a profitability claim.</div>
</body>
</html>
"""


def write_final_launch_files(out_dir: Path, model: dict[str, Any]) -> dict[str, str]:
    assert_safety_contract()
    out_dir.mkdir(parents=True, exist_ok=True)

    model_json = out_dir / "MODULE_138_FINAL_LAUNCH_PACK_MODEL.json"
    launch_html = out_dir / "MODULE_138_FINAL_LAUNCH_PACK.html"
    open_bat = out_dir / "OPEN_HQE_FORWARD_PAPER_DASHBOARD_SUITE.bat"

    model_json.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    launch_html.write_text(render_final_launch_html(model), encoding="utf-8")

    lines = ["@echo off", "setlocal", f'start "" "{launch_html}"']
    for key in ("operator_console_html", "history_index_html", "latest_dashboard_html"):
        record = model["artifacts"][key]
        if record["present"]:
            lines.append(f'start "" "{record["path"]}"')
    lines.append("endlocal")
    open_bat.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "final_launch_model_json": str(model_json),
        "final_launch_html": str(launch_html),
        "open_dashboard_suite_bat": str(open_bat),
    }


def default_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_138_FINAL_LAUNCH_PACK_{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--runs-root", type=Path, default=Path("D:/HQE_BACKTEST_RUNS"))
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = args.out_dir or default_out_dir()
    model = build_final_launch_model(FinalLaunchInputs(runs_root=args.runs_root, out_dir=out_dir))
    files = write_final_launch_files(out_dir, model)
    print(json.dumps({**model, **files, "out_dir": str(out_dir)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
