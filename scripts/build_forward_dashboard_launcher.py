"""
Module 135: Dashboard Launcher / Latest Dry-Run Integration

Finds the latest forward paper evidence pack and builds a local static
read-only dashboard using Module 134.

Safety contract:
- Paper/simulation only
- Read-only launcher
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
import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


MODULE_ID = 135
MODULE_NAME = "Dashboard Launcher / Latest Dry-Run Integration"

PAPER_ONLY = True
READ_ONLY_LAUNCHER = True
LOCAL_STATIC_HTML_ONLY = True
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
REAL_MONEY_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False
EXTERNAL_API_ALLOWED = False
PROFITABILITY_CLAIM = False

DAILY_PACK_NAME = "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"
DAILY_SUMMARY_NAME = "MODULE_133_DAILY_SUMMARY.csv"
EVIDENCE_MANIFEST_NAME = "MODULE_133_EVIDENCE_MANIFEST.csv"
SUPERVISOR_SUMMARY_NAME = "MODULE_131_SUPERVISOR_SUMMARY.json"
OVERLAY_JSON_NAME = "MODULE_132_AI_REASON_OVERLAY.json"


@dataclass(frozen=True)
class LauncherInputs:
    runs_root: Path
    evidence_dir: Path | None
    out_dir: Path
    day_label: str | None = None


def assert_safety_contract() -> None:
    if not PAPER_ONLY:
        raise RuntimeError("SAFETY_FAIL: PAPER_ONLY must stay True.")
    if not READ_ONLY_LAUNCHER:
        raise RuntimeError("SAFETY_FAIL: launcher must stay read-only.")
    if not LOCAL_STATIC_HTML_ONLY:
        raise RuntimeError("SAFETY_FAIL: launcher must stay local static HTML only.")

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


def load_module134() -> Any:
    script_path = Path(__file__).resolve().parent / "build_forward_paper_dashboard.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Module 134 dashboard script not found: {script_path}")
    spec = importlib.util.spec_from_file_location("build_forward_paper_dashboard", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Module 134 dashboard script.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def is_evidence_dir(path: Path) -> bool:
    return path.is_dir() and (path / DAILY_PACK_NAME).exists()


def discover_evidence_dirs(runs_root: Path) -> list[Path]:
    if not runs_root.exists() or not runs_root.is_dir():
        return []
    candidates: list[Path] = []
    for child in runs_root.iterdir():
        if is_evidence_dir(child):
            candidates.append(child)
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)


def resolve_evidence_dir(runs_root: Path, evidence_dir: Path | None) -> Path | None:
    if evidence_dir is not None:
        if not evidence_dir.exists() or not evidence_dir.is_dir():
            raise FileNotFoundError(f"Evidence directory not found: {evidence_dir}")
        if not is_evidence_dir(evidence_dir):
            raise FileNotFoundError(f"Evidence directory missing {DAILY_PACK_NAME}: {evidence_dir}")
        return evidence_dir

    discovered = discover_evidence_dirs(runs_root)
    return discovered[0] if discovered else None


def build_no_data_model(inputs: LauncherInputs, reason: str) -> dict[str, Any]:
    return {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "paper_only": True,
        "read_only_launcher": True,
        "local_static_html_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "external_api_allowed": False,
        "profitability_claim": False,
        "launcher_status": "NO_EVIDENCE_FOUND",
        "reason": reason,
        "runs_root": str(inputs.runs_root),
        "evidence_dir": "",
        "day_label": inputs.day_label or "NO_DATA",
        "dashboard_html": "",
        "dashboard_model_json": "",
        "dashboard_summary_csv": "",
    }


def build_launcher(inputs: LauncherInputs) -> dict[str, Any]:
    assert_safety_contract()

    module134 = load_module134()
    evidence_dir = resolve_evidence_dir(inputs.runs_root, inputs.evidence_dir)

    if evidence_dir is None:
        no_data = build_no_data_model(inputs, "No Module 133 daily report pack found under runs root.")
        return no_data

    daily_pack_json = evidence_dir / DAILY_PACK_NAME
    daily_pack = read_json(daily_pack_json)
    day_label = inputs.day_label or str(daily_pack.get("day_label") or evidence_dir.name)

    dashboard_inputs = module134.DashboardInputs(
        day_label=day_label,
        daily_pack_json=daily_pack_json,
        daily_summary_csv=evidence_dir / DAILY_SUMMARY_NAME,
        evidence_manifest_csv=evidence_dir / EVIDENCE_MANIFEST_NAME,
        supervisor_summary_json=evidence_dir / SUPERVISOR_SUMMARY_NAME,
        overlay_json=evidence_dir / OVERLAY_JSON_NAME,
        out_dir=inputs.out_dir,
    )

    dashboard_model = module134.build_dashboard_model(dashboard_inputs)
    dashboard_files = module134.write_dashboard_files(inputs.out_dir, dashboard_model)

    launcher_model = {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "paper_only": True,
        "read_only_launcher": True,
        "local_static_html_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "external_api_allowed": False,
        "profitability_claim": False,
        "launcher_status": "LATEST_EVIDENCE_DASHBOARD_READY",
        "runs_root": str(inputs.runs_root),
        "evidence_dir": str(evidence_dir),
        "day_label": day_label,
        "dashboard_status": dashboard_model.get("dashboard_status", ""),
        "day_status": dashboard_model.get("day_status", ""),
        "signal_generated": dashboard_model.get("signal_generated", False),
        "event": dashboard_model.get("event", ""),
        "action": dashboard_model.get("action", ""),
        "gate": dashboard_model.get("gate", ""),
        "position_state": dashboard_model.get("position_state", ""),
        "ledger_evaluator_status": dashboard_model.get("ledger_evaluator_status", ""),
        "opened_positions": dashboard_model.get("ledger_stats", {}).get("opened_positions", 0),
        "closed_positions": dashboard_model.get("ledger_stats", {}).get("closed_positions", 0),
        "total_paper_pnl": dashboard_model.get("ledger_stats", {}).get("total_paper_pnl", 0.0),
        **dashboard_files,
    }
    return launcher_model


def write_launcher_files(out_dir: Path, model: dict[str, Any]) -> dict[str, str]:
    assert_safety_contract()
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / "MODULE_135_DASHBOARD_LAUNCHER_MODEL.json"
    report_path = out_dir / "MODULE_135_DASHBOARD_LAUNCHER_REPORT.md"
    open_bat = out_dir / "OPEN_LATEST_FORWARD_PAPER_DASHBOARD.bat"

    model_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report_lines = [
        f"# HQE Module {MODULE_ID} - {MODULE_NAME}",
        "",
        "## Safety",
        "- Paper/simulation only: YES",
        "- Read-only launcher: YES",
        "- Local static HTML only: YES",
        "- External API: NO",
        "- Broker execution: NO",
        "- Real orders: NO",
        "- Real money approval: NO",
        "- Auto trading: NO",
        "- Option selling: NO",
        "- Profitability claim: NO",
        "",
        "## Launcher Result",
        f"- Launcher status: {model.get('launcher_status', '')}",
        f"- Runs root: {model.get('runs_root', '')}",
        f"- Evidence dir: {model.get('evidence_dir', '')}",
        f"- Day label: {model.get('day_label', '')}",
        f"- Dashboard status: {model.get('dashboard_status', '')}",
        f"- Day status: {model.get('day_status', '')}",
        f"- Signal generated: {model.get('signal_generated', '')}",
        f"- Event: {model.get('event', '')}",
        f"- Action: {model.get('action', '')}",
        f"- Gate: {model.get('gate', '')}",
        f"- Position state: {model.get('position_state', '')}",
        f"- Ledger/evaluator status: {model.get('ledger_evaluator_status', '')}",
        "",
        "## Dashboard Files",
        f"- Dashboard HTML: {model.get('dashboard_html', '')}",
        f"- Dashboard model JSON: {model.get('dashboard_model_json', '')}",
        f"- Dashboard summary CSV: {model.get('dashboard_summary_csv', '')}",
        "",
        "## Rule",
        "This launcher is read-only forward paper evidence. It is not a profitability claim and not a real-money approval.",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    dashboard_html = str(model.get("dashboard_html", ""))
    if dashboard_html:
        open_bat.write_text(
            "@echo off\n"
            "setlocal\n"
            f'start "" "{dashboard_html}"\n'
            "endlocal\n",
            encoding="utf-8",
        )
    else:
        open_bat.write_text(
            "@echo off\n"
            "echo No dashboard HTML found. Check MODULE_135_DASHBOARD_LAUNCHER_REPORT.md\n"
            "pause\n",
            encoding="utf-8",
        )

    return {
        "launcher_model_json": str(model_path),
        "launcher_report_md": str(report_path),
        "open_latest_dashboard_bat": str(open_bat),
    }


def default_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_135_DASHBOARD_LAUNCHER_{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--runs-root", type=Path, default=Path("D:/HQE_BACKTEST_RUNS"))
    parser.add_argument("--evidence-dir", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--day-label", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = args.out_dir or default_out_dir()
    inputs = LauncherInputs(
        runs_root=args.runs_root,
        evidence_dir=args.evidence_dir,
        out_dir=out_dir,
        day_label=args.day_label,
    )
    model = build_launcher(inputs)
    files = write_launcher_files(out_dir, model)
    result = {**model, **files, "out_dir": str(out_dir)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

