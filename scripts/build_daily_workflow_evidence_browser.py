#!/usr/bin/env python3
"""
HQE Module 143 - Daily Workflow Evidence Index / Operator Evidence Browser

Purpose:
- Build a local, read-only evidence index for the daily paper workflow.
- Create a simple offline HTML browser plus JSON, Markdown, and CSV inventories.
- Highlight Module 140/141/142 artifacts when available.
- Help the operator quickly open evidence files without editing or faking evidence.

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
- This script reads local files and writes only its own Module 143 index outputs.
- It does not place orders, connect to brokers, call external APIs, or modify evidence.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


MODULE_NAME = "Module 143 - Daily Workflow Evidence Index / Operator Evidence Browser"
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
        "This evidence browser is local-only and read-only for existing evidence. "
        "It does not place orders, connect to a broker, call external APIs, "
        "or claim profitability."
    ),
}

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

EVIDENCE_HINTS = (
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
    "HANDOFF",
    "EVIDENCE",
    "VALIDATION",
    "OPERATOR",
    "REPORT",
    "LOG",
)

MODULE_HINTS = {
    "module140": ("MODULE_140", "DAILY_WORKFLOW", "WORKFLOW_REPORT", "FORWARD_PAPER_DAILY"),
    "module141": ("MODULE_141", "OPERATOR_HANDOFF", "CHECKLIST"),
    "module142": ("MODULE_142", "EVIDENCE_VALIDATION", "HANDOFF_VALIDATOR"),
    "dashboard": ("DASHBOARD", "INDEX.HTML", "LAUNCH"),
    "trade_log": ("TRADE_LOG", "FORWARD_TRADE_LOG"),
    "ledger": ("LEDGER", "MASTER_LEDGER"),
    "reason_overlay": ("AI_REASON", "REASON_OVERLAY"),
    "supervisor": ("SUPERVISOR", "INTRADAY"),
}

SAFETY_RISK_PATTERNS = (
    r"\bplace_order\s*\(",
    r"\bcreate_order\s*\(",
    r"\border_send\s*\(",
    r"\bmodify_order\s*\(",
    r"\bcancel_order\s*\(",
    r"\bconnect_broker\s*\(",
    r"\bbroker_login\s*\(",
    r"\blive_trading\s*=\s*true\b",
    r"\breal_money\s*=\s*true\b",
    r"\bauto_trading\s*=\s*true\b",
    r"\boption_selling\s*=\s*true\b",
    r"\bSELL\s+TO\s+OPEN\b",
    r"\bshort\s+option\s+sell\b",
    r"\bapi_key\b",
    r"\baccess_token\b",
    r"\bsecret_key\b",
    r"\bKiteConnect\b",
    r"\bFyersModel\b",
    r"\bUpstox\b",
    r"\bAliceBlue\b",
)


@dataclass(frozen=True)
class EvidenceFile:
    run_dir: Path
    path: Path
    relative_to_run: str
    category: str
    module_tag: str
    size_bytes: int
    modified_time: str
    preview: str
    risk_hits: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_dir": str(self.run_dir),
            "path": str(self.path),
            "relative_to_run": self.relative_to_run,
            "category": self.category,
            "module_tag": self.module_tag,
            "size_bytes": self.size_bytes,
            "modified_time": self.modified_time,
            "preview": self.preview,
            "risk_hits": self.risk_hits,
            "file_uri": self.path.resolve().as_uri() if self.path.exists() else "",
        }


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _safe_walk_files(root: Path, max_scan_files: int) -> Iterable[Path]:
    scanned = 0
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file_name in files:
            if scanned >= max_scan_files:
                return
            scanned += 1
            yield Path(current_root) / file_name


def _read_text_preview(path: Path, max_chars: int = 1200) -> str:
    suffix = path.suffix.lower()
    if suffix not in {".txt", ".md", ".json", ".csv", ".log", ".html", ".htm"}:
        return ""

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"[READ_ERROR] {exc}"

    text = text.replace("\x00", "")
    return text[:max_chars]


def _looks_like_evidence(path: Path) -> bool:
    name_upper = path.name.upper()
    if any(hint in name_upper for hint in EVIDENCE_HINTS):
        return True
    if path.suffix.lower() in {".html", ".htm"} and ("dashboard" in str(path).lower() or "index" in path.name.lower()):
        return True
    return False


def _classify_category(path: Path) -> str:
    name = path.name.upper()
    suffix = path.suffix.lower()

    if "TRADE_LOG" in name:
        return "paper_trade_log"
    if "LEDGER" in name:
        return "forward_ledger"
    if "MODULE_142" in name or "VALIDATION" in name:
        return "evidence_validation"
    if "MODULE_141" in name or "HANDOFF" in name or "CHECKLIST" in name:
        return "operator_handoff"
    if "MODULE_140" in name or "WORKFLOW" in name:
        return "daily_workflow"
    if "AI_REASON" in name or "REASON" in name:
        return "reason_overlay"
    if "SUPERVISOR" in name:
        return "paper_supervisor"
    if "DASHBOARD" in name or "INDEX" in name or suffix in {".html", ".htm"}:
        return "dashboard"
    if "LOG" in name:
        return "diagnostic_log"
    if suffix == ".json":
        return "json_artifact"
    if suffix == ".csv":
        return "csv_artifact"
    if suffix in {".md", ".txt"}:
        return "text_artifact"
    return "other_evidence"


def _classify_module(path: Path) -> str:
    combined = f"{path.name.upper()} {str(path.parent).upper()}"
    for tag, hints in MODULE_HINTS.items():
        if any(hint in combined for hint in hints):
            return tag
    return "general"


def _scan_risks(path: Path, max_chars: int = 200_000) -> List[str]:
    suffix = path.suffix.lower()
    if suffix not in {".txt", ".md", ".json", ".csv", ".log", ".py", ".ps1", ".bat"}:
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return []

    hits: List[str] = []
    for pattern in SAFETY_RISK_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def _run_dir_for_file(path: Path, root: Path) -> Path:
    """Return a useful top-level evidence directory for a file."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return path.parent

    parts = rel.parts
    if len(parts) <= 1:
        return root

    # Keep nested module output with its parent daily folder. Examples:
    # runs/HQE_FORWARD_DAY/MODULE_142_EVIDENCE_VALIDATION/file => runs/HQE_FORWARD_DAY
    return root / parts[0]


def collect_evidence_files(
    runs_root: Path,
    evidence_dir: Optional[Path] = None,
    max_scan_files: int = 30000,
    max_files: int = 1200,
) -> List[EvidenceFile]:
    root = evidence_dir.expanduser() if evidence_dir else runs_root.expanduser()
    if not root.exists() or not root.is_dir():
        return []

    compiled: List[EvidenceFile] = []
    for path in _safe_walk_files(root, max_scan_files=max_scan_files):
        if len(compiled) >= max_files:
            break
        if not path.is_file() or not _looks_like_evidence(path):
            continue

        try:
            run_dir = root if evidence_dir else _run_dir_for_file(path, root)
            rel = str(path.relative_to(run_dir)) if path.is_relative_to(run_dir) else path.name
            stat = path.stat()
            preview = _read_text_preview(path)
            risks = _scan_risks(path)
            compiled.append(
                EvidenceFile(
                    run_dir=run_dir,
                    path=path,
                    relative_to_run=rel,
                    category=_classify_category(path),
                    module_tag=_classify_module(path),
                    size_bytes=stat.st_size,
                    modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                    preview=preview,
                    risk_hits=risks,
                )
            )
        except OSError:
            continue

    compiled.sort(key=lambda item: (item.run_dir.stat().st_mtime if item.run_dir.exists() else 0, item.modified_time), reverse=True)
    return compiled


def group_by_run(files: Sequence[EvidenceFile], max_runs: int = 25) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[EvidenceFile]] = {}
    for item in files:
        grouped.setdefault(str(item.run_dir), []).append(item)

    runs: List[Dict[str, Any]] = []
    for run_dir_str, items in grouped.items():
        run_path = Path(run_dir_str)
        newest_ts = max(item.modified_time for item in items) if items else ""
        categories = sorted({item.category for item in items})
        modules = sorted({item.module_tag for item in items})
        risk_count = sum(1 for item in items if item.risk_hits)
        runs.append(
            {
                "run_dir": run_dir_str,
                "run_name": run_path.name,
                "file_count": len(items),
                "newest_modified_time": newest_ts,
                "categories": categories,
                "modules": modules,
                "risk_file_count": risk_count,
                "files": [item.to_dict() for item in sorted(items, key=lambda f: f.modified_time, reverse=True)],
            }
        )

    runs.sort(key=lambda row: row["newest_modified_time"], reverse=True)
    return runs[:max_runs]


def summarize_browser(files: Sequence[EvidenceFile], runs: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    category_counts: Dict[str, int] = {}
    module_counts: Dict[str, int] = {}
    risk_files = 0

    for item in files:
        category_counts[item.category] = category_counts.get(item.category, 0) + 1
        module_counts[item.module_tag] = module_counts.get(item.module_tag, 0) + 1
        if item.risk_hits:
            risk_files += 1

    status = "PASS"
    if risk_files:
        status = "BLOCKED_SAFETY_RISK"
    elif not files:
        status = "HOLD_NO_EVIDENCE_FOUND"

    return {
        "browser_status": status,
        "run_count": len(runs),
        "file_count": len(files),
        "risk_file_count": risk_files,
        "category_counts": dict(sorted(category_counts.items())),
        "module_counts": dict(sorted(module_counts.items())),
    }


def write_inventory_csv(path: Path, files: Sequence[EvidenceFile]) -> None:
    fieldnames = [
        "run_dir",
        "path",
        "relative_to_run",
        "category",
        "module_tag",
        "size_bytes",
        "modified_time",
        "risk_hits",
        "file_uri",
    ]
    with path.open("w", encoding="utf-8", errors="replace", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in files:
            row = item.to_dict()
            row["risk_hits"] = "; ".join(item.risk_hits)
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def render_markdown(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines: List[str] = []
    lines.append(f"# {report['module']}")
    lines.append("")
    lines.append(f"Generated at: `{report['generated_at']}`")
    lines.append(f"Browser status: `{summary['browser_status']}`")
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
    lines.append("> This is not a profitability claim. This browser is a local evidence index only.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Runs indexed: `{summary['run_count']}`")
    lines.append(f"- Files indexed: `{summary['file_count']}`")
    lines.append(f"- Files with safety-risk hits: `{summary['risk_file_count']}`")
    lines.append("")
    lines.append("## Category Counts")
    lines.append("")
    if summary["category_counts"]:
        for category, count in summary["category_counts"].items():
            lines.append(f"- `{category}`: `{count}`")
    else:
        lines.append("- No evidence categories found.")
    lines.append("")
    lines.append("## Runs")
    lines.append("")
    for run in report["runs"]:
        lines.append(f"### {run['run_name']}")
        lines.append("")
        lines.append(f"- Folder: `{run['run_dir']}`")
        lines.append(f"- Files: `{run['file_count']}`")
        lines.append(f"- Newest modified: `{run['newest_modified_time']}`")
        lines.append(f"- Categories: `{', '.join(run['categories'])}`")
        lines.append(f"- Module tags: `{', '.join(run['modules'])}`")
        lines.append("")
        lines.append("| File | Category | Module | Size | Risk |")
        lines.append("|---|---|---|---:|---|")
        for item in run["files"][:80]:
            risk = "YES" if item["risk_hits"] else "NO"
            lines.append(
                f"| `{item['relative_to_run']}` | `{item['category']}` | `{item['module_tag']}` | {item['size_bytes']} | `{risk}` |"
            )
        lines.append("")
    lines.append("## Operator Handoff")
    lines.append("")
    lines.append("```text")
    lines.append("Module 143 handoff:")
    lines.append("- Browser status:")
    lines.append("- Report folder:")
    lines.append("- HTML browser:")
    lines.append("- Runs indexed:")
    lines.append("- Files indexed:")
    lines.append("- Safety-risk hits:")
    lines.append("- Real money/broker/orders/auto trading/option selling: all NO")
    lines.append("- Profitability claim: NO")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_html(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    status = html.escape(str(summary["browser_status"]))
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
    .risk { font-weight: bold; }
    .small { color: #555; font-size: 12px; }
    details { margin-top: 6px; }
    pre { white-space: pre-wrap; max-height: 220px; overflow: auto; background: #fafafa; padding: 8px; border: 1px solid #eee; }
    """

    parts: List[str] = []
    parts.append("<!doctype html><html><head><meta charset='utf-8'>")
    parts.append(f"<title>{html.escape(MODULE_NAME)}</title>")
    parts.append(f"<style>{css}</style></head><body>")
    parts.append(f"<h1>{html.escape(MODULE_NAME)}</h1>")
    parts.append("<div class='card'>")
    parts.append(f"<p>Generated at: <code>{generated}</code></p>")
    parts.append(f"<p>Browser status: <span class='status'>{status}</span></p>")
    parts.append("<p><strong>Safety:</strong> paper/simulation only; real money NO; broker execution NO; real orders NO; auto trading NO; option selling NO; external API NO; profitability claim NO.</p>")
    parts.append("<p><strong>This is not a profitability claim.</strong> This is a local read-only evidence browser.</p>")
    parts.append("</div>")

    parts.append("<div class='card'><h2>Summary</h2>")
    parts.append("<ul>")
    parts.append(f"<li>Runs indexed: <code>{summary['run_count']}</code></li>")
    parts.append(f"<li>Files indexed: <code>{summary['file_count']}</code></li>")
    parts.append(f"<li>Files with safety-risk hits: <code>{summary['risk_file_count']}</code></li>")
    parts.append("</ul></div>")

    parts.append("<div class='card'><h2>Category Counts</h2><table><tr><th>Category</th><th>Count</th></tr>")
    for category, count in summary["category_counts"].items():
        parts.append(f"<tr><td><code>{html.escape(category)}</code></td><td>{count}</td></tr>")
    if not summary["category_counts"]:
        parts.append("<tr><td colspan='2'>No evidence categories found.</td></tr>")
    parts.append("</table></div>")

    for run in report["runs"]:
        parts.append("<div class='card'>")
        parts.append(f"<h2>{html.escape(run['run_name'])}</h2>")
        parts.append(f"<p class='small'>Folder: <code>{html.escape(run['run_dir'])}</code></p>")
        parts.append(f"<p>Files: <code>{run['file_count']}</code> | Newest: <code>{html.escape(run['newest_modified_time'])}</code> | Risk files: <code>{run['risk_file_count']}</code></p>")
        parts.append("<table><tr><th>Open</th><th>File</th><th>Category</th><th>Module</th><th>Size</th><th>Risk</th><th>Preview</th></tr>")
        for item in run["files"]:
            risk_text = "YES" if item["risk_hits"] else "NO"
            risk_detail = "; ".join(item["risk_hits"])
            preview = html.escape((item.get("preview") or "")[:1200])
            file_uri = html.escape(item.get("file_uri") or "")
            rel = html.escape(item.get("relative_to_run") or "")
            category = html.escape(item.get("category") or "")
            module = html.escape(item.get("module_tag") or "")
            size = item.get("size_bytes", "")
            parts.append("<tr>")
            parts.append(f"<td><a href='{file_uri}'>open</a></td>")
            parts.append(f"<td><code>{rel}</code></td>")
            parts.append(f"<td>{category}</td>")
            parts.append(f"<td>{module}</td>")
            parts.append(f"<td>{size}</td>")
            parts.append(f"<td class='risk'>{html.escape(risk_text)}")
            if risk_detail:
                parts.append(f"<br><span class='small'>{html.escape(risk_detail)}</span>")
            parts.append("</td>")
            if preview:
                parts.append(f"<td><details><summary>preview</summary><pre>{preview}</pre></details></td>")
            else:
                parts.append("<td class='small'>No text preview</td>")
            parts.append("</tr>")
        parts.append("</table></div>")

    parts.append("</body></html>")
    return "\n".join(parts)


def build_evidence_browser(
    runs_root: Path,
    output_dir: Optional[Path] = None,
    evidence_dir: Optional[Path] = None,
    max_scan_files: int = 30000,
    max_files: int = 1200,
    max_runs: int = 25,
) -> Dict[str, Any]:
    files = collect_evidence_files(
        runs_root=runs_root,
        evidence_dir=evidence_dir,
        max_scan_files=max_scan_files,
        max_files=max_files,
    )
    runs = group_by_run(files, max_runs=max_runs)
    summary = summarize_browser(files, runs)

    root = evidence_dir.expanduser() if evidence_dir else runs_root.expanduser()
    if output_dir:
        out_dir = output_dir.expanduser()
    else:
        out_dir = root / f"HQE_MODULE_143_EVIDENCE_BROWSER_{_now_stamp()}"

    out_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "module": MODULE_NAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "safety_lock": SAFETY_LOCK,
        "inputs": {
            "runs_root": str(runs_root),
            "evidence_dir": str(evidence_dir) if evidence_dir else None,
            "max_scan_files": max_scan_files,
            "max_files": max_files,
            "max_runs": max_runs,
        },
        "summary": summary,
        "runs": runs,
        "outputs": {},
    }

    json_path = out_dir / "MODULE_143_EVIDENCE_BROWSER_INDEX.json"
    md_path = out_dir / "MODULE_143_EVIDENCE_BROWSER_INDEX.md"
    csv_path = out_dir / "MODULE_143_EVIDENCE_BROWSER_INVENTORY.csv"
    html_path = out_dir / "MODULE_143_EVIDENCE_BROWSER.html"

    report["outputs"] = {
        "output_dir": str(out_dir),
        "html": str(html_path),
        "json": str(json_path),
        "markdown": str(md_path),
        "inventory_csv": str(csv_path),
    }

    json_path.write_text(json.dumps(report, indent=2, default=_json_default), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")
    write_inventory_csv(csv_path, files)

    return report


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="Root folder for HQE backtest/forward runs.")
    parser.add_argument("--evidence-dir", default=None, help="Optional specific daily/evidence folder to index.")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for Module 143 browser reports.")
    parser.add_argument("--max-scan-files", type=int, default=30000, help="Maximum files to scan.")
    parser.add_argument("--max-files", type=int, default=1200, help="Maximum evidence files to include.")
    parser.add_argument("--max-runs", type=int, default=25, help="Maximum run folders to include.")
    parser.add_argument("--print-summary", action="store_true", help="Print concise status and output paths.")
    parser.add_argument(
        "--strict-exit-code",
        action="store_true",
        help="Return exit code 2 if browser status is not PASS.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    report = build_evidence_browser(
        runs_root=Path(args.runs_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        evidence_dir=Path(args.evidence_dir) if args.evidence_dir else None,
        max_scan_files=args.max_scan_files,
        max_files=args.max_files,
        max_runs=args.max_runs,
    )

    if args.print_summary:
        outputs = report["outputs"]
        summary = report["summary"]
        print("MODULE_143_EVIDENCE_BROWSER_CREATED")
        print(f"browser_status={summary['browser_status']}")
        print(f"runs_indexed={summary['run_count']}")
        print(f"files_indexed={summary['file_count']}")
        print(f"risk_file_count={summary['risk_file_count']}")
        print(f"output_dir={outputs.get('output_dir')}")
        print(f"html={outputs.get('html')}")
        print(f"markdown={outputs.get('markdown')}")
        print(f"json={outputs.get('json')}")
        print(f"inventory_csv={outputs.get('inventory_csv')}")
        print("safety=paper_only_no_broker_no_real_orders_no_auto_trading_no_option_selling_no_profitability_claim")

    if args.strict_exit_code and report["summary"]["browser_status"] != "PASS":
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
