from __future__ import annotations

import argparse
import csv
import html
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

MODULE_ID = 140
MODULE_NAME = "Forward Paper Daily Workflow Wrapper / One-Command Daily Run"

PAPER_ONLY = True
READ_ONLY_WORKFLOW_WRAPPER = True
LOCAL_ONLY = True
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
REAL_MONEY_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False
EXTERNAL_API_ALLOWED = False
PROFITABILITY_CLAIM = False

STEP_DEFINITIONS = [
    {"step_id": "operator_console", "title": "Build operator console", "script": "scripts/build_forward_operator_console.py", "out_subdir": "01_OPERATOR_CONSOLE"},
    {"step_id": "final_launch_pack", "title": "Build final launch pack", "script": "scripts/build_forward_dashboard_final_launch_pack.py", "out_subdir": "02_FINAL_LAUNCH_PACK"},
    {"step_id": "ui_smoke_close_pack", "title": "Build UI smoke close pack", "script": "scripts/build_forward_ui_smoke_evidence_close_pack.py", "out_subdir": "03_UI_SMOKE_CLOSE_PACK"},
]

@dataclass(frozen=True)
class WorkflowInputs:
    repo_root: Path
    runs_root: Path
    out_dir: Path
    python_exe: str
    execute_dashboard_suite: bool = False

def now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def assert_safety_contract() -> None:
    if not PAPER_ONLY or not READ_ONLY_WORKFLOW_WRAPPER or not LOCAL_ONLY:
        raise RuntimeError("SAFETY_FAIL: wrapper must remain paper-only/read-only/local-only.")
    blocked = {
        "BROKER_EXECUTION_ALLOWED": BROKER_EXECUTION_ALLOWED,
        "REAL_ORDERS_ALLOWED": REAL_ORDERS_ALLOWED,
        "REAL_MONEY_ALLOWED": REAL_MONEY_ALLOWED,
        "AUTO_TRADING_ALLOWED": AUTO_TRADING_ALLOWED,
        "OPTION_SELLING_ALLOWED": OPTION_SELLING_ALLOWED,
        "EXTERNAL_API_ALLOWED": EXTERNAL_API_ALLOWED,
        "PROFITABILITY_CLAIM": PROFITABILITY_CLAIM,
    }
    enabled = [key for key, value in blocked.items() if value]
    if enabled:
        raise RuntimeError("SAFETY_FAIL: blocked capability enabled: " + ",".join(enabled))

def step_path(inputs: WorkflowInputs, step: dict[str, str]) -> Path:
    return inputs.repo_root / step["script"]

def step_command(inputs: WorkflowInputs, step: dict[str, str]) -> list[str]:
    return [
        inputs.python_exe,
        str(step_path(inputs, step)),
        "--runs-root",
        str(inputs.runs_root),
        "--out-dir",
        str(inputs.out_dir / step["out_subdir"]),
    ]

def plan_step(inputs: WorkflowInputs, step: dict[str, str]) -> dict[str, Any]:
    present = step_path(inputs, step).exists()
    return {
        "step_id": step["step_id"],
        "title": step["title"],
        "script": step["script"],
        "script_present": present,
        "status": "PLAN_READY" if present else "SCRIPT_MISSING",
        "command": step_command(inputs, step),
        "out_dir": str(inputs.out_dir / step["out_subdir"]),
    }

def run_step(inputs: WorkflowInputs, step: dict[str, str]) -> dict[str, Any]:
    logs = inputs.out_dir / "STEP_LOGS"
    logs.mkdir(parents=True, exist_ok=True)
    cmd = step_command(inputs, step)
    started_at = now()
    result = subprocess.run(cmd, cwd=inputs.repo_root, text=True, capture_output=True)
    ended_at = now()
    stdout_log = logs / f"{step['step_id']}.stdout.txt"
    stderr_log = logs / f"{step['step_id']}.stderr.txt"
    stdout_log.write_text(result.stdout or "", encoding="utf-8")
    stderr_log.write_text(result.stderr or "", encoding="utf-8")
    return {
        "step_id": step["step_id"],
        "title": step["title"],
        "started_at": started_at,
        "ended_at": ended_at,
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "out_dir": str(inputs.out_dir / step["out_subdir"]),
    }

def build_daily_workflow_model(inputs: WorkflowInputs) -> dict[str, Any]:
    assert_safety_contract()
    inputs.out_dir.mkdir(parents=True, exist_ok=True)
    planned = [plan_step(inputs, step) for step in STEP_DEFINITIONS]
    missing = [step["script"] for step in planned if not step["script_present"]]
    executed: list[dict[str, Any]] = []

    if inputs.execute_dashboard_suite and not missing:
        for step in STEP_DEFINITIONS:
            item = run_step(inputs, step)
            executed.append(item)
            if not item["passed"]:
                break

    failed = [step["step_id"] for step in executed if not step["passed"]]
    if inputs.execute_dashboard_suite:
        if missing or failed or len(executed) != len(STEP_DEFINITIONS):
            workflow_status = "DAILY_WORKFLOW_REVIEW_REQUIRED"
            workflow_decision = "REVIEW_REQUIRED_PAPER_ONLY"
        else:
            workflow_status = "DAILY_WORKFLOW_EXECUTION_PASS"
            workflow_decision = "DAILY_WORKFLOW_READY_PAPER_ONLY"
    else:
        if missing:
            workflow_status = "DAILY_WORKFLOW_PLAN_REVIEW_REQUIRED"
            workflow_decision = "REVIEW_REQUIRED_PAPER_ONLY"
        else:
            workflow_status = "DAILY_WORKFLOW_PLAN_READY"
            workflow_decision = "PLAN_READY_PAPER_ONLY"

    return {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "created_at": now(),
        "paper_only": True,
        "read_only_workflow_wrapper": True,
        "local_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "external_api_allowed": False,
        "profitability_claim": False,
        "repo_root": str(inputs.repo_root),
        "runs_root": str(inputs.runs_root),
        "out_dir": str(inputs.out_dir),
        "execute_dashboard_suite": inputs.execute_dashboard_suite,
        "workflow_status": workflow_status,
        "workflow_decision": workflow_decision,
        "missing_scripts": missing,
        "failed_steps": failed,
        "planned_steps": planned,
        "executed_steps": executed,
        "operator_instruction": "Paper-only local dashboard workflow. No broker execution, no real orders, no auto trading, no option selling, no external API, and no profitability claim.",
    }

def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)

def render_workflow_html(model: dict[str, Any]) -> str:
    plan_rows = "".join(
        "<tr>"
        f"<td>{esc(item['step_id'])}</td>"
        f"<td>{esc(item['title'])}</td>"
        f"<td>{esc(item['script_present'])}</td>"
        f"<td>{esc(item['status'])}</td>"
        f"<td>{esc(item['out_dir'])}</td>"
        "</tr>"
        for item in model["planned_steps"]
    )

    if model["executed_steps"]:
        exec_rows = "".join(
            "<tr>"
            f"<td>{esc(item['step_id'])}</td>"
            f"<td>{esc(item['passed'])}</td>"
            f"<td>{esc(item['exit_code'])}</td>"
            f"<td>{esc(item['stdout_log'])}</td>"
            f"<td>{esc(item['stderr_log'])}</td>"
            "</tr>"
            for item in model["executed_steps"]
        )
    else:
        exec_rows = "<tr><td colspan='5'>No steps executed. Plan/report mode only.</td></tr>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HQE Forward Paper Daily Workflow</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;background:#07111f;color:#e5e7eb;margin:0}}
header,main{{padding:24px}}
.panel,.banner{{background:#1e293b;border:1px solid #334155;border-radius:14px;padding:18px;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:9px;border-bottom:1px solid #334155;text-align:left;vertical-align:top}}
footer{{padding:24px;color:#94a3b8}}
</style>
</head>
<body>
<header>
<h1>HQE Forward Paper Daily Workflow</h1>
<p>Module {MODULE_ID} - {esc(MODULE_NAME)} | Created: {esc(model['created_at'])}</p>
</header>
<main>
<section class="banner">
<h2>{esc(model['workflow_status'])}</h2>
<p>{esc(model['operator_instruction'])}</p>
</section>
<section class="panel">
<h2>Workflow Result</h2>
<table>
<tr><th>Decision</th><td>{esc(model['workflow_decision'])}</td></tr>
<tr><th>Execute dashboard suite</th><td>{esc(model['execute_dashboard_suite'])}</td></tr>
<tr><th>Missing scripts</th><td>{esc(', '.join(model['missing_scripts']) if model['missing_scripts'] else 'NONE')}</td></tr>
<tr><th>Failed steps</th><td>{esc(', '.join(model['failed_steps']) if model['failed_steps'] else 'NONE')}</td></tr>
</table>
</section>
<section class="panel">
<h2>Safety Lock</h2>
<table>
<tr><th>Paper/simulation only</th><td>YES</td></tr>
<tr><th>Read-only workflow wrapper</th><td>YES</td></tr>
<tr><th>Local-only</th><td>YES</td></tr>
<tr><th>External API</th><td>NO</td></tr>
<tr><th>Broker execution</th><td>NO</td></tr>
<tr><th>Real orders</th><td>NO</td></tr>
<tr><th>Auto trading</th><td>NO</td></tr>
<tr><th>Option selling</th><td>NO</td></tr>
<tr><th>Profitability claim</th><td>NO</td></tr>
</table>
</section>
<section class="panel">
<h2>Planned Steps</h2>
<table><thead><tr><th>Step</th><th>Title</th><th>Script present</th><th>Status</th><th>Output</th></tr></thead><tbody>{plan_rows}</tbody></table>
</section>
<section class="panel">
<h2>Executed Steps</h2>
<table><thead><tr><th>Step</th><th>Passed</th><th>Exit</th><th>Stdout log</th><th>Stderr log</th></tr></thead><tbody>{exec_rows}</tbody></table>
</section>
</main>
<footer>This is not a profitability claim. No real-money approval.</footer>
</body>
</html>"""

def write_daily_workflow_files(out_dir: Path, model: dict[str, Any]) -> dict[str, str]:
    assert_safety_contract()
    out_dir.mkdir(parents=True, exist_ok=True)
    model_json = out_dir / "MODULE_140_DAILY_WORKFLOW_MODEL.json"
    report_md = out_dir / "MODULE_140_DAILY_WORKFLOW_REPORT.md"
    summary_csv = out_dir / "MODULE_140_DAILY_WORKFLOW_SUMMARY.csv"
    html_path = out_dir / "MODULE_140_DAILY_WORKFLOW.html"
    run_bat = out_dir / "RUN_HQE_FORWARD_PAPER_DAILY_WORKFLOW.bat"

    model_json.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(render_workflow_html(model), encoding="utf-8")
    report_md.write_text(
        f"# HQE Module {MODULE_ID} - {MODULE_NAME}\n\n"
        "## Result\n"
        f"- Workflow status: {model['workflow_status']}\n"
        f"- Workflow decision: {model['workflow_decision']}\n"
        f"- Execute dashboard suite: {model['execute_dashboard_suite']}\n"
        f"- Missing scripts: {', '.join(model['missing_scripts']) if model['missing_scripts'] else 'NONE'}\n"
        f"- Failed steps: {', '.join(model['failed_steps']) if model['failed_steps'] else 'NONE'}\n\n"
        "## Safety\n"
        "- Paper/simulation only: YES\n"
        "- Read-only workflow wrapper: YES\n"
        "- Local-only: YES\n"
        "- External API: NO\n"
        "- Broker execution: NO\n"
        "- Real orders: NO\n"
        "- Real money approval: NO\n"
        "- Auto trading: NO\n"
        "- Option selling: NO\n"
        "- Profitability claim: NO\n\n"
        "This wrapper refreshes local dashboard evidence only. It is not a profitability claim and not a real-money approval.\n",
        encoding="utf-8",
    )
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["created_at", "workflow_status", "workflow_decision", "execute_dashboard_suite", "missing_scripts", "failed_steps", "paper_only", "broker_execution_allowed", "real_orders_allowed", "auto_trading_allowed", "profitability_claim"])
        writer.writeheader()
        writer.writerow({
            "created_at": model["created_at"],
            "workflow_status": model["workflow_status"],
            "workflow_decision": model["workflow_decision"],
            "execute_dashboard_suite": model["execute_dashboard_suite"],
            "missing_scripts": ";".join(model["missing_scripts"]),
            "failed_steps": ";".join(model["failed_steps"]),
            "paper_only": model["paper_only"],
            "broker_execution_allowed": model["broker_execution_allowed"],
            "real_orders_allowed": model["real_orders_allowed"],
            "auto_trading_allowed": model["auto_trading_allowed"],
            "profitability_claim": model["profitability_claim"],
        })
    run_bat.write_text(
        "@echo off\n"
        "setlocal\n"
        f'cd /d "{model["repo_root"]}"\n'
        f'"{sys.executable}" "scripts\\run_forward_paper_daily_workflow.py" --repo-root "{model["repo_root"]}" --runs-root "{model["runs_root"]}" --execute-dashboard-suite\n'
        "endlocal\n",
        encoding="utf-8",
    )
    return {
        "daily_workflow_model_json": str(model_json),
        "daily_workflow_report_md": str(report_md),
        "daily_workflow_summary_csv": str(summary_csv),
        "daily_workflow_html": str(html_path),
        "run_daily_workflow_bat": str(run_bat),
    }

def default_out_dir() -> Path:
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_140_DAILY_WORKFLOW_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--runs-root", type=Path, default=Path("D:/HQE_BACKTEST_RUNS"))
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--python-exe", default=sys.executable)
    parser.add_argument("--execute-dashboard-suite", action="store_true")
    return parser

def main() -> int:
    args = build_parser().parse_args()
    out_dir = args.out_dir or default_out_dir()
    model = build_daily_workflow_model(
        WorkflowInputs(
            repo_root=args.repo_root,
            runs_root=args.runs_root,
            out_dir=out_dir,
            python_exe=args.python_exe,
            execute_dashboard_suite=args.execute_dashboard_suite,
        )
    )
    files = write_daily_workflow_files(out_dir, model)
    print(json.dumps({**model, **files}, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
