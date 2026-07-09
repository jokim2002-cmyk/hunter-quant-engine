#!/usr/bin/env python3
"""
HQE Module 141 - Daily Workflow Operator Checklist / Handoff Pack

Purpose:
- Build a local, read-only operator checklist and handoff pack for the HQE
  forward paper daily workflow.
- Detect and summarize Module 140 daily workflow output when available.
- Write human-readable Markdown, machine-readable JSON, and a file-inspection CSV.

Safety lock:
- Paper/simulation only.
- No real money.
- No broker execution.
- No real orders.
- No auto trading.
- No option selling.
- No external API.
- No profitability claim.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


MODULE_NAME = "Module 141 - Daily Workflow Operator Checklist / Handoff Pack"
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
        "This pack is an operator checklist and handoff artifact only. "
        "It does not place orders, connect to a broker, call external APIs, "
        "or claim profitability."
    ),
}

MODULE_140_HINTS = (
    "daily_workflow",
    "workflow_summary",
    "daily_summary",
    "forward_paper_daily",
    "daily_report",
    "operator_summary",
)

IMPORTANT_FILE_HINTS = (
    "FORWARD_VALIDATION_MASTER_LEDGER",
    "DAY_",
    "TRADE_LOG",
    "SUPERVISOR",
    "AI_REASON",
    "DAILY_REPORT",
    "DASHBOARD",
    "LAUNCH",
    "INDEX",
    "WORKFLOW",
    "SUMMARY",
    "CHECKLIST",
    "EVIDENCE",
    "LOG",
)

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
}


@dataclass(frozen=True)
class SourceContext:
    source_status: str
    source_file: Optional[Path]
    source_dir: Optional[Path]
    source_kind: str
    parsed_summary: Dict[str, Any]


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _read_text(path: Path, max_chars: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError as exc:
        return f"[READ_ERROR] {exc}"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # JSON may be malformed in interrupted runs.
        return {"_parse_error": str(exc)}

    if isinstance(data, dict):
        return data

    return {"_json_root_type": type(data).__name__, "value_preview": str(data)[:500]}


def _csv_preview(path: Path, max_rows: int = 5) -> Dict[str, Any]:
    result: Dict[str, Any] = {"headers": [], "preview_rows": [], "row_count_observed": 0}
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            result["headers"] = list(reader.fieldnames or [])
            for row in reader:
                result["row_count_observed"] += 1
                if len(result["preview_rows"]) < max_rows:
                    result["preview_rows"].append(dict(row))
    except Exception as exc:
        result["_parse_error"] = str(exc)
    return result


def _markdown_preview(path: Path) -> Dict[str, Any]:
    text = _read_text(path)
    lines = text.splitlines()
    headings = [line.strip() for line in lines if line.strip().startswith("#")][:10]
    return {
        "line_count_observed": len(lines),
        "headings": headings,
        "preview": "\n".join(lines[:20]),
    }


def _summarize_source_file(path: Path) -> Tuple[str, Dict[str, Any]]:
    suffix = path.suffix.lower()
    base: Dict[str, Any] = {
        "file_name": path.name,
        "file_path": str(path),
        "file_suffix": suffix,
        "file_size_bytes": path.stat().st_size if path.exists() else None,
        "file_modified_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
        if path.exists()
        else None,
    }

    if suffix == ".json":
        base.update(_load_json(path))
        return "json", base
    if suffix == ".csv":
        base.update(_csv_preview(path))
        return "csv", base
    if suffix in {".md", ".txt", ".log"}:
        base.update(_markdown_preview(path))
        return "text", base

    base["preview"] = _read_text(path, max_chars=1500)
    return "unknown_text", base


def _looks_like_module_140_output(path: Path) -> bool:
    name = path.name.lower()
    suffix_ok = path.suffix.lower() in {".json", ".csv", ".md", ".txt", ".log"}
    if not suffix_ok:
        return False

    return any(hint in name for hint in MODULE_140_HINTS)


def _safe_walk_files(root: Path, max_scan_files: int) -> Iterable[Path]:
    scanned = 0
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file_name in files:
            if scanned >= max_scan_files:
                return
            scanned += 1
            yield Path(current_root) / file_name


def _latest_by_mtime(paths: Iterable[Path]) -> Optional[Path]:
    candidates: List[Path] = []
    for path in paths:
        try:
            if path.exists() and path.is_file():
                candidates.append(path)
        except OSError:
            continue

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)


def find_source_context(
    runs_root: Path,
    daily_output_file: Optional[Path] = None,
    daily_output_dir: Optional[Path] = None,
    max_scan_files: int = 20000,
) -> SourceContext:
    """Find and summarize the latest likely Module 140 daily workflow output."""
    if daily_output_file:
        file_path = daily_output_file.expanduser()
        if file_path.exists() and file_path.is_file():
            kind, summary = _summarize_source_file(file_path)
            return SourceContext("found_explicit_file", file_path, file_path.parent, kind, summary)
        return SourceContext(
            "explicit_file_missing",
            file_path,
            file_path.parent,
            "missing",
            {"missing_file": str(file_path)},
        )

    if daily_output_dir:
        dir_path = daily_output_dir.expanduser()
        if dir_path.exists() and dir_path.is_dir():
            latest = _latest_by_mtime(
                path for path in dir_path.iterdir() if path.is_file() and _looks_like_module_140_output(path)
            )
            if latest:
                kind, summary = _summarize_source_file(latest)
                return SourceContext("found_explicit_dir", latest, dir_path, kind, summary)

            return SourceContext(
                "explicit_dir_found_no_summary_file",
                None,
                dir_path,
                "directory",
                {"directory": str(dir_path), "note": "No obvious Module 140 summary file found inside this folder."},
            )

        return SourceContext(
            "explicit_dir_missing",
            None,
            dir_path,
            "missing",
            {"missing_dir": str(dir_path)},
        )

    root = runs_root.expanduser()
    if not root.exists() or not root.is_dir():
        return SourceContext(
            "runs_root_missing",
            None,
            None,
            "missing",
            {"runs_root": str(root), "note": "Runs root does not exist on this machine."},
        )

    latest_match = _latest_by_mtime(
        path for path in _safe_walk_files(root, max_scan_files=max_scan_files) if _looks_like_module_140_output(path)
    )

    if latest_match:
        kind, summary = _summarize_source_file(latest_match)
        return SourceContext("found_by_scan", latest_match, latest_match.parent, kind, summary)

    return SourceContext(
        "not_found",
        None,
        root,
        "none",
        {
            "runs_root": str(root),
            "note": (
                "No obvious Module 140 daily workflow output was found. "
                "The checklist was still generated as a generic paper-only operator handoff pack."
            ),
        },
    )


def _extract_status_fields(parsed: Dict[str, Any]) -> Dict[str, Any]:
    wanted_names = (
        "status",
        "decision",
        "run_status",
        "workflow_status",
        "daily_status",
        "paper_status",
        "trade_count",
        "completed_trades",
        "planned_signals",
        "forward_paper_trades",
        "day_number",
        "run_date",
        "trading_date",
        "output_dir",
        "report_dir",
        "dashboard_dir",
        "dashboard_index",
        "master_ledger",
    )

    extracted: Dict[str, Any] = {}
    for key, value in parsed.items():
        key_lower = str(key).lower()
        if key_lower in wanted_names or any(name in key_lower for name in wanted_names):
            extracted[str(key)] = value

    return extracted


def _inspect_files(source_dir: Optional[Path], max_files: int = 250) -> List[Dict[str, Any]]:
    if not source_dir or not source_dir.exists() or not source_dir.is_dir():
        return []

    rows: List[Dict[str, Any]] = []
    scanned = 0
    for path in sorted(source_dir.rglob("*")):
        if scanned >= max_files:
            break
        try:
            if path.is_dir():
                continue
            rel = str(path.relative_to(source_dir))
            name_upper = path.name.upper()
            important = any(hint in name_upper for hint in IMPORTANT_FILE_HINTS)
            if not important:
                continue

            scanned += 1
            rows.append(
                {
                    "relative_path": rel,
                    "file_name": path.name,
                    "size_bytes": path.stat().st_size,
                    "modified_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                    "inspection_note": _inspection_note(path.name),
                }
            )
        except OSError:
            continue

    return rows


def _inspection_note(file_name: str) -> str:
    upper = file_name.upper()
    if "TRADE_LOG" in upper:
        return "Paper trade log. Zero trades is not a failure by itself; fake trades are not allowed."
    if "LEDGER" in upper:
        return "Forward validation ledger / evidence continuity file."
    if "SUPERVISOR" in upper:
        return "Intraday paper supervisor output or log."
    if "AI_REASON" in upper or "REASON" in upper:
        return "AI reason overlay / explanation artifact. Evidence only, not a trading recommendation."
    if "DASHBOARD" in upper or "INDEX" in upper or "LAUNCH" in upper:
        return "Local dashboard/operator UI file."
    if "REPORT" in upper or "SUMMARY" in upper:
        return "Daily paper workflow summary/report artifact."
    if "LOG" in upper:
        return "Diagnostic log. Inspect errors before continuing."
    return "Related operator workflow artifact."


def build_pack(
    runs_root: Path,
    output_dir: Optional[Path] = None,
    daily_output_file: Optional[Path] = None,
    daily_output_dir: Optional[Path] = None,
    max_scan_files: int = 20000,
) -> Dict[str, Any]:
    context = find_source_context(
        runs_root=runs_root,
        daily_output_file=daily_output_file,
        daily_output_dir=daily_output_dir,
        max_scan_files=max_scan_files,
    )

    if output_dir:
        out_dir = output_dir.expanduser()
    elif context.source_dir and context.source_dir.exists():
        out_dir = context.source_dir / "MODULE_141_OPERATOR_HANDOFF"
    else:
        out_dir = runs_root.expanduser() / f"HQE_MODULE_141_OPERATOR_HANDOFF_{_now_stamp()}"

    out_dir.mkdir(parents=True, exist_ok=True)

    source_status_fields = _extract_status_fields(context.parsed_summary)
    file_rows = _inspect_files(context.source_dir)

    pack: Dict[str, Any] = {
        "module": MODULE_NAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "safety_lock": SAFETY_LOCK,
        "source": {
            "source_status": context.source_status,
            "source_file": str(context.source_file) if context.source_file else None,
            "source_dir": str(context.source_dir) if context.source_dir else None,
            "source_kind": context.source_kind,
            "extracted_status_fields": source_status_fields,
        },
        "operator_checklist": {
            "before_market": [
                "Confirm this is paper/simulation only. Real money, broker execution, real orders, auto trading, and option selling must remain OFF.",
                "Open the latest daily workflow wrapper from Module 140 and confirm the expected trading date/day folder.",
                "Confirm data/input files are local and no external API is required for this run.",
                "Confirm previous day handoff, logs, and dashboard files are available if the workflow depends on them.",
                "Do not invent trades. If there is no signal or no valid paper trade, record zero trades honestly.",
            ],
            "during_paper_run": [
                "Run only the approved local paper workflow commands.",
                "Watch the supervisor/log output for exceptions, missing files, or safety-lock warnings.",
                "Do not manually force entries/exits to improve results.",
                "If any broker/live-order path appears, stop immediately and mark the run blocked.",
            ],
            "after_close": [
                "Generate or collect the daily report pack, AI reason overlay, dashboard files, and workflow summary.",
                "Inspect paper trade log, master ledger, supervisor output, and diagnostic logs.",
                "Record real forward evidence exactly as produced. Zero trades is allowed; fake trades are not.",
                "Copy the final status, output folder path, and any blocker/error tail into the next handoff.",
            ],
            "handoff_to_next_chat": [
                "Share latest commit, git status, daily output folder, generated Module 141 handoff folder, and final paper workflow status.",
                "Mention whether Module 140 output was detected by this script.",
                "Mention evidence counts only as paper validation evidence, not as a profitability claim.",
            ],
            "stop_conditions": [
                "Any real broker connection, order-placement path, token use, or live-account behavior.",
                "Any auto-trading behavior beyond local paper/simulation artifact generation.",
                "Missing or corrupted critical daily output files.",
                "Unexpected exception without a saved diagnostic log/tail.",
                "Manual/fake trades or edited results.",
            ],
        },
        "file_inspection_targets": file_rows,
        "outputs": {},
    }

    json_path = out_dir / "MODULE_141_OPERATOR_HANDOFF.json"
    md_path = out_dir / "MODULE_141_OPERATOR_HANDOFF.md"
    csv_path = out_dir / "MODULE_141_FILE_INSPECTION_TARGETS.csv"

    json_path.write_text(json.dumps(pack, indent=2, default=_json_default), encoding="utf-8")
    md_path.write_text(render_markdown(pack), encoding="utf-8")
    write_file_csv(csv_path, file_rows)

    pack["outputs"] = {
        "output_dir": str(out_dir),
        "json": str(json_path),
        "markdown": str(md_path),
        "file_targets_csv": str(csv_path),
    }

    # Re-write JSON with outputs populated.
    json_path.write_text(json.dumps(pack, indent=2, default=_json_default), encoding="utf-8")

    return pack


def write_file_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = ["relative_path", "file_name", "size_bytes", "modified_time", "inspection_note"]
    with path.open("w", encoding="utf-8", errors="replace", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def render_markdown(pack: Dict[str, Any]) -> str:
    safety = pack["safety_lock"]
    source = pack["source"]
    checklist = pack["operator_checklist"]
    file_rows = pack["file_inspection_targets"]

    lines: List[str] = []
    lines.append(f"# {pack['module']}")
    lines.append("")
    lines.append(f"Generated at: `{pack['generated_at']}`")
    lines.append("")
    lines.append("## Safety Lock")
    lines.append("")
    lines.append("- Paper/simulation only: `YES`")
    lines.append(f"- Real money: `{'YES' if safety['real_money'] else 'NO'}`")
    lines.append(f"- Broker execution: `{'YES' if safety['broker_execution'] else 'NO'}`")
    lines.append(f"- Real orders: `{'YES' if safety['real_orders'] else 'NO'}`")
    lines.append(f"- Auto trading: `{'YES' if safety['auto_trading'] else 'NO'}`")
    lines.append(f"- Option selling: `{'YES' if safety['option_selling'] else 'NO'}`")
    lines.append(f"- External API: `{'YES' if safety['external_api'] else 'NO'}`")
    lines.append(f"- Profitability claim: `{'YES' if safety['profitability_claim'] else 'NO'}`")
    lines.append("")
    lines.append("> This is not a profitability claim. This handoff pack is for local paper-validation operations only.")
    lines.append("")
    lines.append("## Module 140 Daily Workflow Source")
    lines.append("")
    lines.append(f"- Source status: `{source.get('source_status')}`")
    lines.append(f"- Source kind: `{source.get('source_kind')}`")
    lines.append(f"- Source file: `{source.get('source_file')}`")
    lines.append(f"- Source dir: `{source.get('source_dir')}`")
    lines.append("")

    extracted = source.get("extracted_status_fields") or {}
    if extracted:
        lines.append("### Extracted Status Fields")
        lines.append("")
        for key in sorted(extracted):
            value = extracted[key]
            if isinstance(value, (dict, list)):
                value_text = json.dumps(value, default=_json_default)[:500]
            else:
                value_text = str(value)[:500]
            lines.append(f"- `{key}`: `{value_text}`")
        lines.append("")
    else:
        lines.append("No structured status fields were extracted from the detected source.")
        lines.append("")

    lines.append("## Operator Checklist")
    lines.append("")
    for section, items in checklist.items():
        lines.append(f"### {section.replace('_', ' ').title()}")
        lines.append("")
        for item in items:
            lines.append(f"- [ ] {item}")
        lines.append("")

    lines.append("## Files To Inspect")
    lines.append("")
    if file_rows:
        lines.append("| File | Size | Inspection note |")
        lines.append("|---|---:|---|")
        for row in file_rows[:80]:
            lines.append(
                f"| `{row.get('relative_path', '')}` | {row.get('size_bytes', '')} | {row.get('inspection_note', '')} |"
            )
        lines.append("")
    else:
        lines.append("No related files were found for inspection in the detected source folder.")
        lines.append("")

    lines.append("## Next Handoff Template")
    lines.append("")
    lines.append("```text")
    lines.append("Module 141 handoff:")
    lines.append("- Repo status: CLEAN / NOT CLEAN")
    lines.append("- Latest commit:")
    lines.append("- Daily workflow output folder:")
    lines.append("- Module 141 output folder:")
    lines.append("- Module 140 source detected: YES / NO")
    lines.append("- Paper workflow final status:")
    lines.append("- Blockers/errors:")
    lines.append("- Real money/broker/orders/auto trading/option selling: all NO")
    lines.append("- Profitability claim: NO")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="Root folder for HQE backtest/forward runs.")
    parser.add_argument("--output-dir", default=None, help="Optional explicit output folder for Module 141 pack.")
    parser.add_argument("--daily-output-file", default=None, help="Optional explicit Module 140 daily workflow summary file.")
    parser.add_argument("--daily-output-dir", default=None, help="Optional explicit Module 140 daily workflow output folder.")
    parser.add_argument("--max-scan-files", type=int, default=20000, help="Safety limit for scanning runs-root files.")
    parser.add_argument("--print-summary", action="store_true", help="Print concise output paths/status after generation.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    pack = build_pack(
        runs_root=Path(args.runs_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        daily_output_file=Path(args.daily_output_file) if args.daily_output_file else None,
        daily_output_dir=Path(args.daily_output_dir) if args.daily_output_dir else None,
        max_scan_files=args.max_scan_files,
    )

    if args.print_summary:
        source = pack["source"]
        outputs = pack["outputs"]
        print("MODULE_141_OPERATOR_HANDOFF_CREATED")
        print(f"source_status={source.get('source_status')}")
        print(f"source_file={source.get('source_file')}")
        print(f"output_dir={outputs.get('output_dir')}")
        print(f"markdown={outputs.get('markdown')}")
        print(f"json={outputs.get('json')}")
        print(f"file_targets_csv={outputs.get('file_targets_csv')}")
        print("safety=paper_only_no_broker_no_real_orders_no_auto_trading_no_option_selling_no_profitability_claim")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
