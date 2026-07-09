#!/usr/bin/env python3
"""
HQE Module 144 - One-click Daily Operator Control Center / Final Local Workflow Launcher

Purpose:
- Provide a final local-only operator control center for the forward paper daily workflow.
- Optionally run approved local HQE paper-workflow helper scripts in safe sequence.
- Produce a single operator-facing HTML control center plus JSON/Markdown/CSV reports.
- Keep the workflow auditable and read-only with respect to existing evidence.

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
- This script only launches approved local repository scripts.
- It does not connect to brokers, call external APIs, place orders, or modify old evidence.
- It writes only Module 144 control-center outputs.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


MODULE_NAME = "Module 144 - One-click Daily Operator Control Center / Final Local Workflow Launcher"
DEFAULT_RUNS_ROOT = Path(r"D:\HQE_BACKTEST_RUNS")

SAFETY_LOCK: Dict[str, Any] = {
    "paper_simulation_only": True,
    "real_money": False,
    "broker_execution": False,
    "real_orders": False,
    "auto_trading": False,
    "option_selling": False,
    "external_api": False,
    "profitability_claim": False,
    "note": (
        "This control center is local-only and paper-only. It can launch approved "
        "local report/index scripts, but it does not place orders, connect to brokers, "
        "call external APIs, or claim profitability."
    ),
}

# Only these local scripts may be launched by the control center.
# Missing optional scripts are reported as WARN, not faked.
APPROVED_STEPS: List[Dict[str, Any]] = [
    {
        "step_id": "module141_operator_handoff",
        "title": "Module 141 Operator Checklist / Handoff Pack",
        "script": "build_daily_workflow_operator_checklist.py",
        "required": True,
        "args": ["--runs-root", "{runs_root}", "--print-summary"],
    },
    {
        "step_id": "module142_evidence_validator",
        "title": "Module 142 Evidence Validator / Handoff Integrity Check",
        "script": "validate_daily_workflow_evidence_handoff.py",
        "required": True,
        "args": ["--runs-root", "{runs_root}", "--print-summary"],
    },
    {
        "step_id": "module143_evidence_browser",
        "title": "Module 143 Evidence Browser / Operator Evidence Index",
        "script": "build_daily_workflow_evidence_browser.py",
        "required": True,
        "args": ["--runs-root", "{runs_root}", "--print-summary"],
    },
]

OPTIONAL_MODULE_140_HINTS = (
    "run_forward_paper_daily_workflow.py",
    "run_forward_paper_daily_wrapper.py",
    "build_forward_paper_daily_workflow.py",
    "forward_paper_daily_workflow.py",
)


@dataclass(frozen=True)
class StepResult:
    step_id: str
    title: str
    script_path: Optional[Path]
    status: str
    return_code: Optional[int]
    stdout_tail: str
    command: List[str]
    started_at: str
    finished_at: str
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "script_path": str(self.script_path) if self.script_path else None,
            "status": self.status,
            "return_code": self.return_code,
            "stdout_tail": self.stdout_tail,
            "command": self.command,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "note": self.note,
        }


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _tail_text(text: str, max_chars: int = 4000) -> str:
    text = text.replace("\x00", "")
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def detect_repo_root(explicit_repo_root: Optional[Path] = None) -> Path:
    if explicit_repo_root:
        return explicit_repo_root.expanduser().resolve()

    # Running from repo root is the normal HQE path.
    cwd = Path.cwd().resolve()
    if (cwd / "scripts").exists() and (cwd / "tests").exists():
        return cwd

    # Running from scripts directory.
    if cwd.name.lower() == "scripts" and (cwd.parent / "tests").exists():
        return cwd.parent

    return cwd


def approved_script_path(repo_root: Path, script_name: str) -> Path:
    return repo_root / "scripts" / script_name


def find_optional_module140_script(repo_root: Path) -> Optional[Path]:
    scripts_dir = repo_root / "scripts"
    for name in OPTIONAL_MODULE_140_HINTS:
        candidate = scripts_dir / name
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def build_command(
    python_exe: Path,
    script_path: Path,
    args_template: Sequence[str],
    runs_root: Path,
) -> List[str]:
    replacements = {
        "{runs_root}": str(runs_root),
    }
    args: List[str] = []
    for item in args_template:
        args.append(replacements.get(item, item))
    return [str(python_exe), str(script_path), *args]


def command_is_safe(command: Sequence[str], repo_root: Path) -> bool:
    """Allow only local python.exe -> repo/scripts/*.py commands with no external URLs."""
    if len(command) < 2:
        return False

    script = Path(command[1])
    try:
        script_resolved = script.resolve()
        scripts_dir = (repo_root / "scripts").resolve()
        if scripts_dir not in script_resolved.parents:
            return False
    except OSError:
        return False

    lowered = " ".join(command).lower()
    blocked_tokens = (
        "http://",
        "https://",
        "place_order",
        "create_order",
        "broker_login",
        "connect_broker",
        "access_token",
        "api_key",
        "secret_key",
        "real_money=true",
        "auto_trading=true",
        "option_selling=true",
    )
    return not any(token in lowered for token in blocked_tokens)


def run_step(
    step: Dict[str, Any],
    repo_root: Path,
    python_exe: Path,
    runs_root: Path,
    execute: bool,
    timeout_seconds: int,
) -> StepResult:
    started = _iso_now()
    script_path = approved_script_path(repo_root, str(step["script"]))
    title = str(step["title"])
    step_id = str(step["step_id"])

    if not script_path.exists():
        finished = _iso_now()
        status = "MISSING_REQUIRED_SCRIPT" if step.get("required") else "MISSING_OPTIONAL_SCRIPT"
        return StepResult(
            step_id=step_id,
            title=title,
            script_path=script_path,
            status=status,
            return_code=None,
            stdout_tail="",
            command=[],
            started_at=started,
            finished_at=finished,
            note="Script not found. No fake result was generated.",
        )

    command = build_command(
        python_exe=python_exe,
        script_path=script_path,
        args_template=step.get("args", []),
        runs_root=runs_root,
    )

    if not command_is_safe(command, repo_root):
        finished = _iso_now()
        return StepResult(
            step_id=step_id,
            title=title,
            script_path=script_path,
            status="BLOCKED_UNSAFE_COMMAND",
            return_code=None,
            stdout_tail="",
            command=command,
            started_at=started,
            finished_at=finished,
            note="Command failed local safety allow-list checks.",
        )

    if not execute:
        finished = _iso_now()
        return StepResult(
            step_id=step_id,
            title=title,
            script_path=script_path,
            status="PLANNED_NOT_EXECUTED",
            return_code=None,
            stdout_tail="",
            command=command,
            started_at=started,
            finished_at=finished,
            note="Plan-only mode. Use --execute-approved-steps to run local approved steps.",
        )

    try:
        proc = subprocess.run(
            command,
            cwd=str(repo_root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
        status = "PASS" if proc.returncode == 0 else "FAIL"
        return StepResult(
            step_id=step_id,
            title=title,
            script_path=script_path,
            status=status,
            return_code=proc.returncode,
            stdout_tail=_tail_text(proc.stdout),
            command=command,
            started_at=started,
            finished_at=_iso_now(),
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return StepResult(
            step_id=step_id,
            title=title,
            script_path=script_path,
            status="TIMEOUT",
            return_code=None,
            stdout_tail=_tail_text(output),
            command=command,
            started_at=started,
            finished_at=_iso_now(),
            note=f"Timed out after {timeout_seconds} seconds.",
        )
    except Exception as exc:
        return StepResult(
            step_id=step_id,
            title=title,
            script_path=script_path,
            status="ERROR",
            return_code=None,
            stdout_tail="",
            command=command,
            started_at=started,
            finished_at=_iso_now(),
            note=str(exc),
        )


def build_manual_launch_commands(repo_root: Path, runs_root: Path) -> List[Dict[str, str]]:
    commands: List[Dict[str, str]] = []
    for step in APPROVED_STEPS:
        script_path = approved_script_path(repo_root, str(step["script"]))
        command = build_command(Path(r".\.venv\Scripts\python.exe"), script_path, step["args"], runs_root)
        commands.append(
            {
                "step_id": str(step["step_id"]),
                "title": str(step["title"]),
                "command": " ".join(f'"{part}"' if " " in part else part for part in command),
                "script_exists": str(script_path.exists()),
            }
        )
    return commands


def summarize_status(step_results: Sequence[StepResult]) -> str:
    statuses = {step.status for step in step_results}
    if any(status in statuses for status in {"BLOCKED_UNSAFE_COMMAND"}):
        return "BLOCKED_SAFETY_RISK"
    if any(status in statuses for status in {"FAIL", "TIMEOUT", "ERROR"}):
        return "HOLD_STEP_FAILURE"
    if any(status in statuses for status in {"MISSING_REQUIRED_SCRIPT"}):
        return "HOLD_REQUIRED_SCRIPT_MISSING"
    if all(status == "PLANNED_NOT_EXECUTED" for status in statuses):
        return "READY_PLAN_ONLY"
    if "PLANNED_NOT_EXECUTED" in statuses:
        return "PASS_WITH_PLAN_ONLY_STEPS"
    return "PASS"


def write_steps_csv(path: Path, steps: Sequence[StepResult]) -> None:
    fieldnames = [
        "step_id",
        "title",
        "script_path",
        "status",
        "return_code",
        "started_at",
        "finished_at",
        "note",
        "command",
        "stdout_tail",
    ]
    with path.open("w", encoding="utf-8", errors="replace", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for step in steps:
            row = step.to_dict()
            row["command"] = " ".join(row.get("command") or [])
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# {report['module']}")
    lines.append("")
    lines.append(f"Generated at: `{report['generated_at']}`")
    lines.append(f"Control-center status: `{report['control_center_status']}`")
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
    lines.append("")
    lines.append("> This is not a profitability claim. This control center is a local paper-workflow launcher/index only.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    for key, value in report["inputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Step Results")
    lines.append("")
    lines.append("| Step | Status | Return code | Script |")
    lines.append("|---|---|---:|---|")
    for step in report["steps"]:
        lines.append(
            f"| `{step['step_id']}` | `{step['status']}` | `{step.get('return_code')}` | `{step.get('script_path')}` |"
        )
    lines.append("")
    lines.append("## Manual Commands")
    lines.append("")
    lines.append("Use these only if you want to run each local report/index step manually.")
    lines.append("")
    for command in report["manual_launch_commands"]:
        lines.append(f"### {command['title']}")
        lines.append("")
        lines.append("```powershell")
        lines.append(command["command"])
        lines.append("```")
        lines.append("")
    lines.append("## Operator Handoff")
    lines.append("")
    lines.append("```text")
    lines.append("Module 144 handoff:")
    lines.append("- Control-center status:")
    lines.append("- Report folder:")
    lines.append("- HTML control center:")
    lines.append("- Executed approved steps: YES / NO")
    lines.append("- Failed/missing steps:")
    lines.append("- Real money/broker/orders/auto trading/option selling: all NO")
    lines.append("- Profitability claim: NO")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_html(report: Dict[str, Any]) -> str:
    status = html.escape(str(report["control_center_status"]))
    generated = html.escape(str(report["generated_at"]))

    css = """
    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f7f7; color: #222; }
    h1, h2, h3 { color: #111; }
    .card { background: white; border: 1px solid #ddd; border-radius: 10px; padding: 16px; margin: 14px 0; }
    .status { font-weight: bold; padding: 4px 8px; border-radius: 6px; background: #eee; }
    table { width: 100%; border-collapse: collapse; background: white; }
    th, td { border: 1px solid #ddd; padding: 7px; vertical-align: top; font-size: 13px; }
    th { background: #f0f0f0; text-align: left; }
    code { background: #f1f1f1; padding: 2px 4px; border-radius: 4px; }
    pre { white-space: pre-wrap; max-height: 260px; overflow: auto; background: #fafafa; padding: 8px; border: 1px solid #eee; }
    .small { color: #555; font-size: 12px; }
    """

    parts: List[str] = []
    parts.append("<!doctype html><html><head><meta charset='utf-8'>")
    parts.append(f"<title>{html.escape(MODULE_NAME)}</title>")
    parts.append(f"<style>{css}</style></head><body>")
    parts.append(f"<h1>{html.escape(MODULE_NAME)}</h1>")
    parts.append("<div class='card'>")
    parts.append(f"<p>Generated at: <code>{generated}</code></p>")
    parts.append(f"<p>Control-center status: <span class='status'>{status}</span></p>")
    parts.append("<p><strong>Safety:</strong> paper/simulation only; real money NO; broker execution NO; real orders NO; auto trading NO; option selling NO; external API NO; profitability claim NO.</p>")
    parts.append("<p><strong>This is not a profitability claim.</strong> This is a local paper-workflow launcher/index only.</p>")
    parts.append("</div>")

    parts.append("<div class='card'><h2>Output Files</h2><ul>")
    for key, value in report["outputs"].items():
        safe_value = html.escape(str(value))
        try:
            uri = Path(str(value)).resolve().as_uri()
            parts.append(f"<li>{html.escape(key)}: <a href='{html.escape(uri)}'><code>{safe_value}</code></a></li>")
        except Exception:
            parts.append(f"<li>{html.escape(key)}: <code>{safe_value}</code></li>")
    parts.append("</ul></div>")

    parts.append("<div class='card'><h2>Step Results</h2>")
    parts.append("<table><tr><th>Step</th><th>Status</th><th>Return code</th><th>Script</th><th>Output tail</th></tr>")
    for step in report["steps"]:
        parts.append("<tr>")
        parts.append(f"<td><code>{html.escape(step['step_id'])}</code><br>{html.escape(step['title'])}</td>")
        parts.append(f"<td><strong>{html.escape(step['status'])}</strong></td>")
        parts.append(f"<td>{html.escape(str(step.get('return_code')))}</td>")
        parts.append(f"<td><code>{html.escape(str(step.get('script_path')))}</code></td>")
        tail = html.escape(str(step.get("stdout_tail") or step.get("note") or ""))
        parts.append(f"<td><details><summary>view</summary><pre>{tail}</pre></details></td>")
        parts.append("</tr>")
    parts.append("</table></div>")

    parts.append("<div class='card'><h2>Manual Local Commands</h2>")
    parts.append("<p class='small'>Only approved local report/index scripts. No broker/API/order command is included.</p>")
    for command in report["manual_launch_commands"]:
        parts.append(f"<h3>{html.escape(command['title'])}</h3>")
        parts.append(f"<pre>{html.escape(command['command'])}</pre>")
    parts.append("</div>")

    parts.append("</body></html>")
    return "\n".join(parts)


def build_control_center(
    repo_root: Path,
    runs_root: Path,
    output_dir: Optional[Path] = None,
    python_exe: Optional[Path] = None,
    execute_approved_steps: bool = False,
    timeout_seconds: int = 120,
) -> Dict[str, Any]:
    repo_root = detect_repo_root(repo_root)
    runs_root = runs_root.expanduser()
    python_exe = python_exe.expanduser() if python_exe else Path(sys.executable)

    if output_dir:
        out_dir = output_dir.expanduser()
    else:
        out_dir = runs_root / f"HQE_MODULE_144_OPERATOR_CONTROL_CENTER_{_now_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    steps: List[StepResult] = []
    for step in APPROVED_STEPS:
        steps.append(
            run_step(
                step=step,
                repo_root=repo_root,
                python_exe=python_exe,
                runs_root=runs_root,
                execute=execute_approved_steps,
                timeout_seconds=timeout_seconds,
            )
        )

    optional_module140 = find_optional_module140_script(repo_root)

    status = summarize_status(steps)
    report: Dict[str, Any] = {
        "module": MODULE_NAME,
        "generated_at": _iso_now(),
        "control_center_status": status,
        "safety_lock": SAFETY_LOCK,
        "inputs": {
            "repo_root": str(repo_root),
            "runs_root": str(runs_root),
            "python_exe": str(python_exe),
            "execute_approved_steps": execute_approved_steps,
            "timeout_seconds": timeout_seconds,
            "optional_module140_script_detected": str(optional_module140) if optional_module140 else None,
        },
        "steps": [step.to_dict() for step in steps],
        "manual_launch_commands": build_manual_launch_commands(repo_root, runs_root),
        "outputs": {},
    }

    json_path = out_dir / "MODULE_144_OPERATOR_CONTROL_CENTER.json"
    md_path = out_dir / "MODULE_144_OPERATOR_CONTROL_CENTER.md"
    html_path = out_dir / "MODULE_144_OPERATOR_CONTROL_CENTER.html"
    csv_path = out_dir / "MODULE_144_OPERATOR_CONTROL_CENTER_STEPS.csv"

    report["outputs"] = {
        "output_dir": str(out_dir),
        "html": str(html_path),
        "json": str(json_path),
        "markdown": str(md_path),
        "steps_csv": str(csv_path),
    }

    json_path.write_text(json.dumps(report, indent=2, default=_json_default), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")
    write_steps_csv(csv_path, steps)

    return report


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--repo-root", default=None, help="HQE repository root. Defaults to current folder.")
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="HQE runs root folder.")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for the control-center report.")
    parser.add_argument("--python-exe", default=None, help="Python executable. Defaults to current interpreter.")
    parser.add_argument(
        "--execute-approved-steps",
        action="store_true",
        help="Run approved local Module 141/142/143 report/index scripts.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=120, help="Timeout per approved step.")
    parser.add_argument("--print-summary", action="store_true", help="Print concise status and output paths.")
    parser.add_argument(
        "--strict-exit-code",
        action="store_true",
        help="Return exit code 2 when control-center status is not PASS or READY_PLAN_ONLY.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    report = build_control_center(
        repo_root=Path(args.repo_root) if args.repo_root else Path.cwd(),
        runs_root=Path(args.runs_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        python_exe=Path(args.python_exe) if args.python_exe else None,
        execute_approved_steps=args.execute_approved_steps,
        timeout_seconds=args.timeout_seconds,
    )

    if args.print_summary:
        outputs = report["outputs"]
        print("MODULE_144_OPERATOR_CONTROL_CENTER_CREATED")
        print(f"control_center_status={report['control_center_status']}")
        print(f"execute_approved_steps={report['inputs'].get('execute_approved_steps')}")
        print(f"output_dir={outputs.get('output_dir')}")
        print(f"html={outputs.get('html')}")
        print(f"markdown={outputs.get('markdown')}")
        print(f"json={outputs.get('json')}")
        print(f"steps_csv={outputs.get('steps_csv')}")
        print("safety=paper_only_no_broker_no_real_orders_no_auto_trading_no_option_selling_no_profitability_claim")

    if args.strict_exit_code and report["control_center_status"] not in {"PASS", "READY_PLAN_ONLY"}:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
