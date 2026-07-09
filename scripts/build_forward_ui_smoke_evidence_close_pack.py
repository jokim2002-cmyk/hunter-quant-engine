from __future__ import annotations

import argparse
import csv
import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


MODULE_ID = 139
MODULE_NAME = "UI Smoke Test / Final Dashboard Evidence Close Pack"

PAPER_ONLY = True
READ_ONLY_CLOSE_PACK = True
LOCAL_STATIC_HTML_ONLY = True
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
REAL_MONEY_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False
EXTERNAL_API_ALLOWED = False
PROFITABILITY_CLAIM = False

ARTIFACTS = {
    "final_launch_html": "MODULE_138_FINAL_LAUNCH_PACK.html",
    "operator_console_html": "MODULE_137_OPERATOR_CONSOLE.html",
    "operator_console_model_json": "MODULE_137_OPERATOR_CONSOLE_MODEL.json",
    "history_index_html": "MODULE_136_DASHBOARD_HISTORY_INDEX.html",
    "history_model_json": "MODULE_136_DASHBOARD_HISTORY_INDEX_MODEL.json",
    "latest_dashboard_html": "MODULE_134_FORWARD_PAPER_DASHBOARD.html",
    "daily_pack_json": "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json",
}

HTML_EXPECTATIONS = {
    "final_launch_html": ["HQE Dashboard Final Launch Pack", "Safety Lock", "not a profitability claim"],
    "operator_console_html": ["HQE Forward Paper Operator Console", "Safety Lock", "not a profitability claim"],
    "history_index_html": ["HQE Forward Paper History Index", "Paper/simulation only", "not a profitability claim"],
    "latest_dashboard_html": ["Safety", "Paper", "not a profitability claim"],
}


@dataclass(frozen=True)
class SmokeInputs:
    runs_root: Path
    out_dir: Path


def assert_safety_contract() -> None:
    if not PAPER_ONLY:
        raise RuntimeError("SAFETY_FAIL: PAPER_ONLY must stay True.")
    if not READ_ONLY_CLOSE_PACK:
        raise RuntimeError("SAFETY_FAIL: close pack must stay read-only.")
    if not LOCAL_STATIC_HTML_ONLY:
        raise RuntimeError("SAFETY_FAIL: close pack must stay local static HTML only.")

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


def safe_read_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def safe_read_json(path: Path | None) -> dict[str, Any]:
    text = safe_read_text(path)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def latest_file(root: Path, filename: str) -> Path | None:
    if not root.exists() or not root.is_dir():
        return None
    try:
        matches = [path for path in root.rglob(filename) if path.is_file()]
    except Exception:
        return None
    if not matches:
        return None
    return sorted(matches, key=lambda item: item.stat().st_mtime, reverse=True)[0]


def artifact_record(root: Path, key: str, filename: str) -> dict[str, Any]:
    path = latest_file(root, filename)
    if path is None:
        return {"key": key, "filename": filename, "present": False, "path": "", "modified_at": "", "size_bytes": 0}
    return {
        "key": key,
        "filename": filename,
        "present": True,
        "path": str(path),
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "size_bytes": path.stat().st_size,
    }


def check_html(record: dict[str, Any], terms: list[str]) -> dict[str, Any]:
    if not record.get("present"):
        return {"key": record["key"], "passed": False, "reason": "MISSING_HTML_ARTIFACT", "missing_terms": terms}

    text = safe_read_text(Path(str(record["path"])))
    missing = [term for term in terms if term.lower() not in text.lower()]
    passed = len(missing) == 0
    return {"key": record["key"], "passed": passed, "reason": "PASS" if passed else "HTML_TERMS_MISSING", "missing_terms": missing}


def build_smoke_model(inputs: SmokeInputs) -> dict[str, Any]:
    assert_safety_contract()

    artifacts = {key: artifact_record(inputs.runs_root, key, filename) for key, filename in ARTIFACTS.items()}
    html_checks = {key: check_html(artifacts[key], terms) for key, terms in HTML_EXPECTATIONS.items()}

    operator_model = safe_read_json(Path(artifacts["operator_console_model_json"]["path"]) if artifacts["operator_console_model_json"]["present"] else None)
    history_model = safe_read_json(Path(artifacts["history_model_json"]["path"]) if artifacts["history_model_json"]["present"] else None)
    daily_pack = safe_read_json(Path(artifacts["daily_pack_json"]["path"]) if artifacts["daily_pack_json"]["present"] else None)

    present_count = len([item for item in artifacts.values() if item["present"]])
    missing_artifacts = [key for key, item in artifacts.items() if not item["present"]]
    failed_html_checks = [key for key, item in html_checks.items() if not item["passed"]]

    if missing_artifacts or failed_html_checks:
        smoke_status = "UI_SMOKE_REVIEW_REQUIRED"
        close_decision = "REVIEW_REQUIRED_PAPER_ONLY"
    else:
        smoke_status = "UI_SMOKE_PASS_CLOSE_PACK_READY"
        close_decision = "CLOSE_PACK_READY_PAPER_ONLY"

    return {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "paper_only": True,
        "read_only_close_pack": True,
        "local_static_html_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "external_api_allowed": False,
        "profitability_claim": False,
        "runs_root": str(inputs.runs_root),
        "smoke_status": smoke_status,
        "close_decision": close_decision,
        "present_artifacts": present_count,
        "missing_artifacts": missing_artifacts,
        "failed_html_checks": failed_html_checks,
        "operator_status": str(operator_model.get("operator_status", "")),
        "latest_day_label": str(operator_model.get("latest_day_label", daily_pack.get("day_label", ""))),
        "latest_event": str(operator_model.get("latest_event", daily_pack.get("event", ""))),
        "latest_action": str(operator_model.get("latest_action", daily_pack.get("action", ""))),
        "latest_position_state": str(operator_model.get("latest_position_state", daily_pack.get("position_state", ""))),
        "history_status": str(history_model.get("history_status", "")),
        "total_history_records": int(float(history_model.get("total_records", 0) or 0)),
        "artifacts": artifacts,
        "html_checks": html_checks,
    }


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def link(path_text: str, label: str) -> str:
    if not path_text:
        return '<span class="missing">Missing</span>'
    try:
        href = Path(path_text).resolve().as_uri()
    except Exception:
        href = path_text
    return f'<a href="{esc(href)}">{esc(label)}</a>'


def render_close_pack_html(model: dict[str, Any]) -> str:
    artifact_rows = ""
    for key, record in model["artifacts"].items():
        artifact_rows += f"""
<tr>
  <td>{esc(key)}</td>
  <td>{esc(record["present"])}</td>
  <td>{esc(record["filename"])}</td>
  <td>{esc(record["size_bytes"])}</td>
  <td>{link(record["path"], "Open")}</td>
</tr>
"""

    check_rows = ""
    for key, check in model["html_checks"].items():
        check_rows += f"""
<tr>
  <td>{esc(key)}</td>
  <td>{esc(check["passed"])}</td>
  <td>{esc(check["reason"])}</td>
  <td>{esc(", ".join(check["missing_terms"]))}</td>
</tr>
"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HQE UI Smoke Evidence Close Pack</title>
<style>
body {{ margin:0; font-family:Arial,Helvetica,sans-serif; background:#08111f; color:#e5e7eb; }}
header {{ padding:24px; background:#111827; border-bottom:1px solid #334155; }}
main {{ padding:24px; }}
.banner,.panel {{ background:#1e293b; border:1px solid #334155; border-radius:14px; padding:18px; margin-bottom:16px; }}
.status {{ font-size:26px; font-weight:800; }}
a {{ color:#38bdf8; text-decoration:none; font-weight:700; }}
.missing {{ color:#f87171; font-weight:700; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:9px; border-bottom:1px solid #334155; text-align:left; }}
.footer {{ padding:20px 24px; color:#94a3b8; border-top:1px solid #334155; }}
</style>
</head>
<body>
<header>
<h1>HQE UI Smoke Evidence Close Pack</h1>
<p>Module {MODULE_ID} - {esc(MODULE_NAME)} | Created: {esc(model["created_at"])}</p>
</header>
<main>
<section class="banner">
<div class="status">{esc(model["smoke_status"])}</div>
<p>Close decision: {esc(model["close_decision"])}</p>
</section>

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
<tr><th>Read-only close pack</th><td>YES</td></tr>
<tr><th>Local static HTML only</th><td>YES</td></tr>
<tr><th>External API</th><td>NO</td></tr>
<tr><th>Broker execution</th><td>NO</td></tr>
<tr><th>Real orders</th><td>NO</td></tr>
<tr><th>Auto trading</th><td>NO</td></tr>
<tr><th>Profitability claim</th><td>NO</td></tr>
</table>
</section>

<section class="panel">
<h2>HTML Smoke Checks</h2>
<table>
<thead><tr><th>Artifact</th><th>Passed</th><th>Reason</th><th>Missing terms</th></tr></thead>
<tbody>{check_rows}</tbody>
</table>
</section>

<section class="panel">
<h2>Artifact Inventory</h2>
<table>
<thead><tr><th>Key</th><th>Present</th><th>Filename</th><th>Size bytes</th><th>Open</th></tr></thead>
<tbody>{artifact_rows}</tbody>
</table>
</section>
</main>
<div class="footer">Paper-only UI smoke evidence. No broker execution. No real orders. No auto trading. This is not a profitability claim.</div>
</body>
</html>
"""


def write_close_pack_files(out_dir: Path, model: dict[str, Any]) -> dict[str, str]:
    assert_safety_contract()
    out_dir.mkdir(parents=True, exist_ok=True)

    model_json = out_dir / "MODULE_139_UI_SMOKE_CLOSE_PACK_MODEL.json"
    report_md = out_dir / "MODULE_139_UI_SMOKE_CLOSE_PACK_REPORT.md"
    summary_csv = out_dir / "MODULE_139_UI_SMOKE_CLOSE_PACK_SUMMARY.csv"
    html_path = out_dir / "MODULE_139_UI_SMOKE_CLOSE_PACK.html"
    open_bat = out_dir / "OPEN_MODULE_139_UI_SMOKE_CLOSE_PACK.bat"

    model_json.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(render_close_pack_html(model), encoding="utf-8")

    report_lines = [
        f"# HQE Module {MODULE_ID} - {MODULE_NAME}",
        "",
        "## Result",
        f"- Smoke status: {model['smoke_status']}",
        f"- Close decision: {model['close_decision']}",
        f"- Present artifacts: {model['present_artifacts']}",
        f"- Missing artifacts: {', '.join(model['missing_artifacts']) if model['missing_artifacts'] else 'NONE'}",
        f"- Failed HTML checks: {', '.join(model['failed_html_checks']) if model['failed_html_checks'] else 'NONE'}",
        "",
        "## Safety",
        "- Paper/simulation only: YES",
        "- Read-only close pack: YES",
        "- Local static HTML only: YES",
        "- External API: NO",
        "- Broker execution: NO",
        "- Real orders: NO",
        "- Real money approval: NO",
        "- Auto trading: NO",
        "- Option selling: NO",
        "- Profitability claim: NO",
        "",
        "## Rule",
        "This close pack is UI evidence only. It is not a profitability claim and not a real-money approval.",
    ]
    report_md.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "created_at",
            "smoke_status",
            "close_decision",
            "present_artifacts",
            "missing_artifacts",
            "failed_html_checks",
            "operator_status",
            "latest_day_label",
            "latest_event",
            "latest_action",
            "latest_position_state",
            "history_status",
            "total_history_records",
        ])
        writer.writeheader()
        writer.writerow({
            "created_at": model["created_at"],
            "smoke_status": model["smoke_status"],
            "close_decision": model["close_decision"],
            "present_artifacts": model["present_artifacts"],
            "missing_artifacts": ";".join(model["missing_artifacts"]),
            "failed_html_checks": ";".join(model["failed_html_checks"]),
            "operator_status": model["operator_status"],
            "latest_day_label": model["latest_day_label"],
            "latest_event": model["latest_event"],
            "latest_action": model["latest_action"],
            "latest_position_state": model["latest_position_state"],
            "history_status": model["history_status"],
            "total_history_records": model["total_history_records"],
        })

    open_bat.write_text(
        "@echo off\n"
        "setlocal\n"
        f'start "" "{html_path}"\n'
        "endlocal\n",
        encoding="utf-8",
    )

    return {
        "close_pack_model_json": str(model_json),
        "close_pack_report_md": str(report_md),
        "close_pack_summary_csv": str(summary_csv),
        "close_pack_html": str(html_path),
        "open_close_pack_bat": str(open_bat),
    }


def default_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_139_UI_SMOKE_CLOSE_PACK_{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--runs-root", type=Path, default=Path("D:/HQE_BACKTEST_RUNS"))
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = args.out_dir or default_out_dir()
    model = build_smoke_model(SmokeInputs(runs_root=args.runs_root, out_dir=out_dir))
    files = write_close_pack_files(out_dir, model)
    print(json.dumps({**model, **files, "out_dir": str(out_dir)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
