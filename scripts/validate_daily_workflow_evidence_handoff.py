#!/usr/bin/env python3
"""
HQE Module 142 - Daily Workflow Evidence Validator / Handoff Integrity Check

Purpose:
- Validate the local paper-only daily workflow evidence trail.
- Read Module 141 operator handoff pack when available.
- Validate the referenced Module 140 daily workflow output/source when available.
- Produce read-only integrity reports in JSON, Markdown, and CSV.

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
- This script is local-only and read-only with respect to evidence inputs.
- It does not create, alter, or fake trade evidence.
- It only writes its own Module 142 validation reports.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


MODULE_NAME = "Module 142 - Daily Workflow Evidence Validator / Handoff Integrity Check"
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
        "This validator is local-only and read-only for evidence inputs. "
        "It does not place orders, connect to a broker, call external APIs, "
        "or claim profitability."
    ),
}

REQUIRED_FALSE_SAFETY_FLAGS = (
    "real_money",
    "broker_execution",
    "real_orders",
    "auto_trading",
    "option_selling",
    "external_api",
    "profitability_claim",
)

HANDOFF_JSON_NAME = "MODULE_141_OPERATOR_HANDOFF.json"
HANDOFF_MD_NAME = "MODULE_141_OPERATOR_HANDOFF.md"
HANDOFF_CSV_NAME = "MODULE_141_FILE_INSPECTION_TARGETS.csv"

MODULE_140_NAME_HINTS = (
    "daily_workflow",
    "workflow_summary",
    "daily_summary",
    "forward_paper_daily",
    "daily_report",
    "operator_summary",
)

EVIDENCE_FILE_HINTS = (
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

# Strong code/path patterns that would be suspicious in this paper-only validator context.
# Plain words like "broker" or "real orders" are intentionally NOT included because safety
# reports mention them as disabled states.
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
class CheckResult:
    check_id: str
    status: str
    severity: str
    message: str
    path: Optional[str] = None
    detail: Optional[str] = None

    def as_row(self) -> Dict[str, str]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "path": self.path or "",
            "detail": self.detail or "",
        }


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _read_text(path: Path, max_chars: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError as exc:
        return f"[READ_ERROR] {exc}"


def _load_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return None, str(exc)

    if not isinstance(data, dict):
        return None, f"JSON root is {type(data).__name__}, expected object/dict."

    return data, None


def _file_info(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}

    try:
        stat = path.stat()
    except OSError as exc:
        return {"path": str(path), "exists": False, "error": str(exc)}

    return {
        "path": str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "suffix": path.suffix.lower(),
    }


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


def _looks_like_handoff_json(path: Path) -> bool:
    return path.name == HANDOFF_JSON_NAME


def _looks_like_module_140_output(path: Path) -> bool:
    name = path.name.lower()
    if path.suffix.lower() not in {".json", ".csv", ".md", ".txt", ".log"}:
        return False
    return any(hint in name for hint in MODULE_140_NAME_HINTS)


def find_handoff_json(
    runs_root: Path,
    handoff_dir: Optional[Path] = None,
    handoff_file: Optional[Path] = None,
    max_scan_files: int = 20000,
) -> Optional[Path]:
    if handoff_file:
        return handoff_file.expanduser()

    if handoff_dir:
        candidate = handoff_dir.expanduser() / HANDOFF_JSON_NAME
        if candidate.exists():
            return candidate
        latest_inside = _latest_by_mtime(
            path for path in _safe_walk_files(handoff_dir.expanduser(), max_scan_files=max_scan_files)
            if _looks_like_handoff_json(path)
        )
        return latest_inside

    root = runs_root.expanduser()
    if not root.exists() or not root.is_dir():
        return None

    return _latest_by_mtime(
        path for path in _safe_walk_files(root, max_scan_files=max_scan_files) if _looks_like_handoff_json(path)
    )


def find_module_140_source_from_handoff(handoff: Dict[str, Any]) -> Tuple[Optional[Path], Optional[Path]]:
    source = handoff.get("source") if isinstance(handoff.get("source"), dict) else {}
    file_value = source.get("source_file")
    dir_value = source.get("source_dir")

    source_file = Path(file_value) if isinstance(file_value, str) and file_value.strip() else None
    source_dir = Path(dir_value) if isinstance(dir_value, str) and dir_value.strip() else None

    return source_file, source_dir


def find_module_140_output(
    runs_root: Path,
    explicit_file: Optional[Path] = None,
    explicit_dir: Optional[Path] = None,
    handoff: Optional[Dict[str, Any]] = None,
    max_scan_files: int = 20000,
) -> Optional[Path]:
    if explicit_file:
        return explicit_file.expanduser()

    if explicit_dir:
        dir_path = explicit_dir.expanduser()
        if not dir_path.exists() or not dir_path.is_dir():
            return dir_path / "__MISSING_DIR__"
        return _latest_by_mtime(
            path for path in _safe_walk_files(dir_path, max_scan_files=max_scan_files)
            if _looks_like_module_140_output(path)
        )

    if handoff:
        source_file, source_dir = find_module_140_source_from_handoff(handoff)
        if source_file:
            return source_file
        if source_dir:
            return _latest_by_mtime(
                path for path in _safe_walk_files(source_dir, max_scan_files=max_scan_files)
                if _looks_like_module_140_output(path)
            )

    root = runs_root.expanduser()
    if not root.exists() or not root.is_dir():
        return None

    return _latest_by_mtime(
        path for path in _safe_walk_files(root, max_scan_files=max_scan_files)
        if _looks_like_module_140_output(path)
    )


def validate_safety_lock(data: Dict[str, Any], label: str, source_path: Optional[Path] = None) -> List[CheckResult]:
    checks: List[CheckResult] = []
    lock = data.get("safety_lock")

    if not isinstance(lock, dict):
        return [
            CheckResult(
                check_id=f"{label}.safety_lock.present",
                status="FAIL",
                severity="SAFETY",
                message=f"{label} safety_lock object is missing.",
                path=str(source_path) if source_path else None,
            )
        ]

    checks.append(
        CheckResult(
            check_id=f"{label}.safety_lock.present",
            status="PASS",
            severity="INFO",
            message=f"{label} safety_lock object is present.",
            path=str(source_path) if source_path else None,
        )
    )

    if lock.get("paper_simulation_only") is True:
        checks.append(
            CheckResult(
                check_id=f"{label}.paper_simulation_only.true",
                status="PASS",
                severity="INFO",
                message=f"{label} confirms paper/simulation only.",
                path=str(source_path) if source_path else None,
            )
        )
    else:
        checks.append(
            CheckResult(
                check_id=f"{label}.paper_simulation_only.true",
                status="FAIL",
                severity="SAFETY",
                message=f"{label} does not confirm paper/simulation only.",
                path=str(source_path) if source_path else None,
                detail=f"value={lock.get('paper_simulation_only')!r}",
            )
        )

    for flag in REQUIRED_FALSE_SAFETY_FLAGS:
        value = lock.get(flag)
        if value is False:
            checks.append(
                CheckResult(
                    check_id=f"{label}.{flag}.false",
                    status="PASS",
                    severity="INFO",
                    message=f"{label} {flag} is disabled.",
                    path=str(source_path) if source_path else None,
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_id=f"{label}.{flag}.false",
                    status="FAIL",
                    severity="SAFETY",
                    message=f"{label} {flag} must be false/disabled.",
                    path=str(source_path) if source_path else None,
                    detail=f"value={value!r}",
                )
            )

    return checks


def validate_required_file(path: Optional[Path], check_id: str, label: str, severity: str = "EVIDENCE") -> List[CheckResult]:
    if path is None:
        return [
            CheckResult(
                check_id=check_id,
                status="FAIL",
                severity=severity,
                message=f"{label} path was not found.",
            )
        ]

    if path.exists() and path.is_file() and path.stat().st_size > 0:
        return [
            CheckResult(
                check_id=check_id,
                status="PASS",
                severity="INFO",
                message=f"{label} exists and is non-empty.",
                path=str(path),
                detail=f"size_bytes={path.stat().st_size}",
            )
        ]

    if path.exists() and path.is_file():
        return [
            CheckResult(
                check_id=check_id,
                status="FAIL",
                severity=severity,
                message=f"{label} exists but is empty.",
                path=str(path),
            )
        ]

    return [
        CheckResult(
            check_id=check_id,
            status="FAIL",
            severity=severity,
            message=f"{label} is missing.",
            path=str(path),
        )
    ]


def validate_handoff_files(handoff_json_path: Optional[Path]) -> Tuple[Optional[Dict[str, Any]], List[CheckResult], Dict[str, Any]]:
    checks: List[CheckResult] = []
    inventory: Dict[str, Any] = {"handoff_json": _file_info(handoff_json_path) if handoff_json_path else None}
    handoff_data: Optional[Dict[str, Any]] = None

    checks.extend(validate_required_file(handoff_json_path, "module141.handoff_json.exists", "Module 141 handoff JSON"))

    if handoff_json_path and handoff_json_path.exists() and handoff_json_path.is_file() and handoff_json_path.stat().st_size > 0:
        handoff_data, err = _load_json(handoff_json_path)
        if err:
            checks.append(
                CheckResult(
                    check_id="module141.handoff_json.parse",
                    status="FAIL",
                    severity="EVIDENCE",
                    message="Module 141 handoff JSON could not be parsed.",
                    path=str(handoff_json_path),
                    detail=err,
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_id="module141.handoff_json.parse",
                    status="PASS",
                    severity="INFO",
                    message="Module 141 handoff JSON parsed successfully.",
                    path=str(handoff_json_path),
                )
            )

    if handoff_json_path:
        handoff_dir = handoff_json_path.parent
        md_path = handoff_dir / HANDOFF_MD_NAME
        csv_path = handoff_dir / HANDOFF_CSV_NAME
        inventory["handoff_markdown"] = _file_info(md_path)
        inventory["handoff_file_targets_csv"] = _file_info(csv_path)
        checks.extend(validate_required_file(md_path, "module141.handoff_markdown.exists", "Module 141 handoff Markdown"))
        checks.extend(validate_required_file(csv_path, "module141.file_targets_csv.exists", "Module 141 file inspection CSV"))

    if handoff_data:
        checks.extend(validate_safety_lock(handoff_data, "module141", handoff_json_path))

        module_value = str(handoff_data.get("module", ""))
        if "Module 141" in module_value:
            checks.append(
                CheckResult(
                    check_id="module141.identity",
                    status="PASS",
                    severity="INFO",
                    message="Module 141 identity is present in handoff JSON.",
                    path=str(handoff_json_path),
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_id="module141.identity",
                    status="FAIL",
                    severity="EVIDENCE",
                    message="Module 141 identity is missing or unexpected.",
                    path=str(handoff_json_path),
                    detail=module_value[:200],
                )
            )

    return handoff_data, checks, inventory


def validate_module_140_source(source_file: Optional[Path]) -> Tuple[Optional[Dict[str, Any]], List[CheckResult], Dict[str, Any]]:
    checks: List[CheckResult] = []
    inventory: Dict[str, Any] = {"module140_source": _file_info(source_file) if source_file else None}
    source_data: Optional[Dict[str, Any]] = None

    checks.extend(validate_required_file(source_file, "module140.source.exists", "Module 140 daily workflow source"))

    if not source_file or not source_file.exists() or not source_file.is_file() or source_file.stat().st_size <= 0:
        return None, checks, inventory

    suffix = source_file.suffix.lower()
    if suffix == ".json":
        source_data, err = _load_json(source_file)
        if err:
            checks.append(
                CheckResult(
                    check_id="module140.source_json.parse",
                    status="FAIL",
                    severity="EVIDENCE",
                    message="Module 140 source JSON could not be parsed.",
                    path=str(source_file),
                    detail=err,
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_id="module140.source_json.parse",
                    status="PASS",
                    severity="INFO",
                    message="Module 140 source JSON parsed successfully.",
                    path=str(source_file),
                )
            )

            # Module 140 output may not always have a safety_lock if it predates the
            # validator, so treat missing safety lock as evidence issue, not hidden pass.
            checks.extend(validate_safety_lock(source_data, "module140", source_file))
    elif suffix == ".csv":
        try:
            with source_file.open("r", encoding="utf-8", errors="replace", newline="") as handle:
                reader = csv.reader(handle)
                headers = next(reader, [])
                checks.append(
                    CheckResult(
                        check_id="module140.source_csv.readable",
                        status="PASS",
                        severity="INFO",
                        message="Module 140 source CSV is readable.",
                        path=str(source_file),
                        detail=f"headers={headers[:20]}",
                    )
                )
        except Exception as exc:
            checks.append(
                CheckResult(
                    check_id="module140.source_csv.readable",
                    status="FAIL",
                    severity="EVIDENCE",
                    message="Module 140 source CSV could not be read.",
                    path=str(source_file),
                    detail=str(exc),
                )
            )
    else:
        text = _read_text(source_file, max_chars=4000)
        if "[READ_ERROR]" in text:
            checks.append(
                CheckResult(
                    check_id="module140.source_text.readable",
                    status="FAIL",
                    severity="EVIDENCE",
                    message="Module 140 source text file could not be read.",
                    path=str(source_file),
                    detail=text[:500],
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_id="module140.source_text.readable",
                    status="PASS",
                    severity="INFO",
                    message="Module 140 source text file is readable.",
                    path=str(source_file),
                    detail=f"preview_chars={len(text)}",
                )
            )

    return source_data, checks, inventory


def scan_safety_risks(paths: Sequence[Path], max_chars_per_file: int = 200_000) -> List[CheckResult]:
    checks: List[CheckResult] = []
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in SAFETY_RISK_PATTERNS]

    checked_any = False
    for path in paths:
        if not path or not path.exists() or not path.is_file():
            continue

        checked_any = True
        text = _read_text(path, max_chars=max_chars_per_file)
        hits: List[str] = []
        for regex in compiled:
            if regex.search(text):
                hits.append(regex.pattern)

        if hits:
            checks.append(
                CheckResult(
                    check_id="safety.risk_pattern_scan",
                    status="FAIL",
                    severity="SAFETY",
                    message="Safety-risk pattern found in evidence/handoff file.",
                    path=str(path),
                    detail=", ".join(hits[:10]),
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_id="safety.risk_pattern_scan",
                    status="PASS",
                    severity="INFO",
                    message="No strong safety-risk pattern found in scanned file.",
                    path=str(path),
                )
            )

    if not checked_any:
        checks.append(
            CheckResult(
                check_id="safety.risk_pattern_scan",
                status="WARN",
                severity="EVIDENCE",
                message="No files were available for safety-risk pattern scan.",
            )
        )

    return checks


def inventory_evidence_files(source_dir: Optional[Path], max_files: int = 500) -> List[Dict[str, Any]]:
    if not source_dir or not source_dir.exists() or not source_dir.is_dir():
        return []

    rows: List[Dict[str, Any]] = []
    scanned = 0
    for path in sorted(_safe_walk_files(source_dir, max_scan_files=max_files)):
        try:
            name_upper = path.name.upper()
            if not any(hint in name_upper for hint in EVIDENCE_FILE_HINTS):
                continue

            scanned += 1
            stat = path.stat()
            rows.append(
                {
                    "relative_path": str(path.relative_to(source_dir)),
                    "absolute_path": str(path),
                    "file_name": path.name,
                    "size_bytes": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                    "evidence_note": evidence_note(path.name),
                }
            )
        except OSError:
            continue

        if scanned >= max_files:
            break

    return rows


def evidence_note(file_name: str) -> str:
    upper = file_name.upper()
    if "TRADE_LOG" in upper:
        return "Paper trade log. Zero trades is acceptable; fake trades are blocked."
    if "LEDGER" in upper:
        return "Forward validation ledger / continuity evidence."
    if "WORKFLOW" in upper or "SUMMARY" in upper:
        return "Daily workflow status or summary evidence."
    if "HANDOFF" in upper or "CHECKLIST" in upper:
        return "Operator checklist/handoff evidence."
    if "AI_REASON" in upper or "REASON" in upper:
        return "AI reason overlay evidence; not a trading recommendation."
    if "DASHBOARD" in upper or "INDEX" in upper or "LAUNCH" in upper:
        return "Local dashboard/operator UI evidence."
    if "LOG" in upper:
        return "Diagnostic log; inspect errors or blocker tails."
    return "Related daily workflow evidence file."


def decide_validation_status(checks: Sequence[CheckResult]) -> str:
    if any(check.status == "FAIL" and check.severity == "SAFETY" for check in checks):
        return "BLOCKED_SAFETY_RISK"
    if any(check.status == "FAIL" for check in checks):
        return "HOLD_EVIDENCE_INCOMPLETE"
    if any(check.status == "WARN" for check in checks):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def write_checks_csv(path: Path, checks: Sequence[CheckResult]) -> None:
    fieldnames = ["check_id", "status", "severity", "message", "path", "detail"]
    with path.open("w", encoding="utf-8", errors="replace", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for check in checks:
            writer.writerow(check.as_row())


def write_inventory_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    fieldnames = ["relative_path", "absolute_path", "file_name", "size_bytes", "modified_time", "evidence_note"]
    with path.open("w", encoding="utf-8", errors="replace", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# {report['module']}")
    lines.append("")
    lines.append(f"Generated at: `{report['generated_at']}`")
    lines.append(f"Validation status: `{report['validation_status']}`")
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
    lines.append("> This is not a profitability claim. This validator only checks local paper-workflow evidence integrity.")
    lines.append("")
    lines.append("## Source Paths")
    lines.append("")
    lines.append(f"- Module 141 handoff JSON: `{report['inputs'].get('handoff_json')}`")
    lines.append(f"- Module 140 source file: `{report['inputs'].get('module140_source')}`")
    lines.append(f"- Evidence source dir: `{report['inputs'].get('evidence_source_dir')}`")
    lines.append("")
    lines.append("## Check Summary")
    lines.append("")
    lines.append("| Severity | PASS | WARN | FAIL |")
    lines.append("|---|---:|---:|---:|")
    summary = report.get("check_summary", {})
    for severity in sorted(summary):
        row = summary[severity]
        lines.append(f"| {severity} | {row.get('PASS', 0)} | {row.get('WARN', 0)} | {row.get('FAIL', 0)} |")
    lines.append("")
    lines.append("## Failed / Warning Checks")
    lines.append("")
    problem_checks = [c for c in report.get("checks", []) if c.get("status") in {"FAIL", "WARN"}]
    if problem_checks:
        for check in problem_checks:
            lines.append(f"- `{check.get('status')}` `{check.get('severity')}` `{check.get('check_id')}`: {check.get('message')}")
            if check.get("path"):
                lines.append(f"  - Path: `{check.get('path')}`")
            if check.get("detail"):
                lines.append(f"  - Detail: `{str(check.get('detail'))[:500]}`")
    else:
        lines.append("No failed or warning checks.")
    lines.append("")
    lines.append("## Evidence Inventory")
    lines.append("")
    rows = report.get("evidence_inventory", [])
    if rows:
        lines.append("| File | Size | Note |")
        lines.append("|---|---:|---|")
        for row in rows[:100]:
            lines.append(
                f"| `{row.get('relative_path', '')}` | {row.get('size_bytes', '')} | {row.get('evidence_note', '')} |"
            )
    else:
        lines.append("No evidence files were inventoried from the source directory.")
    lines.append("")
    lines.append("## Operator Decision")
    lines.append("")
    status = report["validation_status"]
    if status == "PASS":
        lines.append("Evidence integrity checks passed for the available local paper-workflow handoff.")
    elif status == "PASS_WITH_WARNINGS":
        lines.append("Evidence can continue only after reviewing warning checks. Do not ignore warnings in final handoff.")
    elif status == "HOLD_EVIDENCE_INCOMPLETE":
        lines.append("Hold. Evidence is incomplete, missing, empty, or unreadable. Do not fake or manually patch trade evidence.")
    else:
        lines.append("Blocked. Safety-risk evidence was detected. Stop and review before any further workflow step.")
    lines.append("")
    lines.append("```text")
    lines.append("Module 142 handoff:")
    lines.append("- Validation status:")
    lines.append("- Module 141 handoff JSON:")
    lines.append("- Module 140 source file:")
    lines.append("- Report folder:")
    lines.append("- Failed checks:")
    lines.append("- Warning checks:")
    lines.append("- Real money/broker/orders/auto trading/option selling: all NO")
    lines.append("- Profitability claim: NO")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def summarize_checks(checks: Sequence[CheckResult]) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for check in checks:
        severity = check.severity
        status = check.status
        summary.setdefault(severity, {"PASS": 0, "WARN": 0, "FAIL": 0})
        summary[severity][status] = summary[severity].get(status, 0) + 1
    return summary


def validate_daily_workflow_evidence(
    runs_root: Path,
    output_dir: Optional[Path] = None,
    handoff_dir: Optional[Path] = None,
    handoff_file: Optional[Path] = None,
    daily_output_dir: Optional[Path] = None,
    daily_output_file: Optional[Path] = None,
    max_scan_files: int = 20000,
) -> Dict[str, Any]:
    runs_root = runs_root.expanduser()
    handoff_json = find_handoff_json(
        runs_root=runs_root,
        handoff_dir=handoff_dir,
        handoff_file=handoff_file,
        max_scan_files=max_scan_files,
    )

    handoff_data, handoff_checks, handoff_inventory = validate_handoff_files(handoff_json)

    module140_source = find_module_140_output(
        runs_root=runs_root,
        explicit_file=daily_output_file,
        explicit_dir=daily_output_dir,
        handoff=handoff_data,
        max_scan_files=max_scan_files,
    )
    module140_data, module140_checks, module140_inventory = validate_module_140_source(module140_source)

    source_dir: Optional[Path] = None
    if module140_source and module140_source.exists() and module140_source.is_file():
        source_dir = module140_source.parent
    elif handoff_json and handoff_json.exists():
        source_dir = handoff_json.parent

    risk_scan_files: List[Path] = []
    if handoff_json:
        risk_scan_files.append(handoff_json)
    if module140_source:
        risk_scan_files.append(module140_source)

    risk_checks = scan_safety_risks(risk_scan_files)
    evidence_inventory = inventory_evidence_files(source_dir)

    checks = [*handoff_checks, *module140_checks, *risk_checks]
    validation_status = decide_validation_status(checks)

    if output_dir:
        out_dir = output_dir.expanduser()
    elif source_dir and source_dir.exists():
        out_dir = source_dir / "MODULE_142_EVIDENCE_VALIDATION"
    else:
        out_dir = runs_root / f"HQE_MODULE_142_EVIDENCE_VALIDATION_{_now_stamp()}"

    out_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "module": MODULE_NAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "validation_status": validation_status,
        "safety_lock": SAFETY_LOCK,
        "inputs": {
            "runs_root": str(runs_root),
            "handoff_json": str(handoff_json) if handoff_json else None,
            "module140_source": str(module140_source) if module140_source else None,
            "evidence_source_dir": str(source_dir) if source_dir else None,
        },
        "input_inventory": {
            "module141": handoff_inventory,
            "module140": module140_inventory,
        },
        "check_summary": summarize_checks(checks),
        "checks": [check.as_row() for check in checks],
        "evidence_inventory": evidence_inventory,
        "outputs": {},
    }

    json_path = out_dir / "MODULE_142_EVIDENCE_VALIDATION_REPORT.json"
    md_path = out_dir / "MODULE_142_EVIDENCE_VALIDATION_REPORT.md"
    checks_csv_path = out_dir / "MODULE_142_EVIDENCE_VALIDATION_CHECKS.csv"
    inventory_csv_path = out_dir / "MODULE_142_EVIDENCE_FILE_INVENTORY.csv"

    report["outputs"] = {
        "output_dir": str(out_dir),
        "json": str(json_path),
        "markdown": str(md_path),
        "checks_csv": str(checks_csv_path),
        "inventory_csv": str(inventory_csv_path),
    }

    json_path.write_text(json.dumps(report, indent=2, default=_json_default), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    write_checks_csv(checks_csv_path, checks)
    write_inventory_csv(inventory_csv_path, evidence_inventory)

    return report


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="Root folder for HQE backtest/forward runs.")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for Module 142 validation report.")
    parser.add_argument("--handoff-dir", default=None, help="Optional folder containing Module 141 handoff files.")
    parser.add_argument("--handoff-file", default=None, help="Optional explicit Module 141 handoff JSON file.")
    parser.add_argument("--daily-output-dir", default=None, help="Optional Module 140 daily workflow output folder.")
    parser.add_argument("--daily-output-file", default=None, help="Optional explicit Module 140 daily workflow source file.")
    parser.add_argument("--max-scan-files", type=int, default=20000, help="Maximum files to scan when finding latest evidence.")
    parser.add_argument("--print-summary", action="store_true", help="Print concise validation status and output paths.")
    parser.add_argument(
        "--strict-exit-code",
        action="store_true",
        help="Return exit code 2 when validation status is not PASS/PASS_WITH_WARNINGS.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    report = validate_daily_workflow_evidence(
        runs_root=Path(args.runs_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        handoff_dir=Path(args.handoff_dir) if args.handoff_dir else None,
        handoff_file=Path(args.handoff_file) if args.handoff_file else None,
        daily_output_dir=Path(args.daily_output_dir) if args.daily_output_dir else None,
        daily_output_file=Path(args.daily_output_file) if args.daily_output_file else None,
        max_scan_files=args.max_scan_files,
    )

    if args.print_summary:
        outputs = report["outputs"]
        print("MODULE_142_EVIDENCE_VALIDATION_CREATED")
        print(f"validation_status={report['validation_status']}")
        print(f"handoff_json={report['inputs'].get('handoff_json')}")
        print(f"module140_source={report['inputs'].get('module140_source')}")
        print(f"output_dir={outputs.get('output_dir')}")
        print(f"markdown={outputs.get('markdown')}")
        print(f"json={outputs.get('json')}")
        print(f"checks_csv={outputs.get('checks_csv')}")
        print(f"inventory_csv={outputs.get('inventory_csv')}")
        print("safety=paper_only_no_broker_no_real_orders_no_auto_trading_no_option_selling_no_profitability_claim")

    if args.strict_exit_code and report["validation_status"] not in {"PASS", "PASS_WITH_WARNINGS"}:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
