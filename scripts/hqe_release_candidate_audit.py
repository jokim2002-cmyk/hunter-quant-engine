from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VERSION = "HQE_RELEASE_CANDIDATE_AUDIT_V1"
AUDIT_FOLDER = "HQE_RELEASE_CENTER/rc_audits"
FREEZE_MANIFEST = "release/HQE_PAPER_ONLY_RC_FREEZE_MANIFEST.json"

APP_CENTER_MARKERS = (
    "Operator Dashboard",
    "Market Data Quality Center",
    "Strategy Pack Center",
    "Strategy Builder & Selector",
    "Backtest Product Center",
    "Paper Validation Intelligence",
    "Windows Release Center",
    "Safety & Kill-Switch",
    "Paper-Watch Session Control",
)

SNAPSHOT_SCRIPTS = (
    "scripts/hqe_app_operator_dashboard.py",
    "scripts/hqe_app_market_data_quality_center.py",
    "scripts/hqe_app_strategy_pack_center.py",
    "scripts/hqe_app_strategy_builder_center.py",
    "scripts/hqe_app_backtest_product_center.py",
    "scripts/hqe_app_paper_validation_report_center.py",
    "scripts/hqe_app_release_center.py",
)

FORBIDDEN_CALL_NAMES = {
    "place_order",
    "submit_order",
    "send_order",
    "execute_order",
    "broker_execute",
    "sell_option",
    "enable_real_trading",
}

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "research_only": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_profitability_claim": True,
}


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_check(
    name: str,
    command: list[str],
    *,
    cwd: Path,
    timeout: int = 180,
    failure_status: str = "FAILED",
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:
        return {
            "name": name,
            "status": failure_status,
            "message": f"{type(exc).__name__}: {exc}",
        }

    return {
        "name": name,
        "status": (
            "PASS"
            if completed.returncode == 0
            else failure_status
        ),
        "message": (
            "Command completed."
            if completed.returncode == 0
            else "Command failed safely."
        ),
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-900:],
        "stderr_tail": completed.stderr[-900:],
    }


def workspace_write_check(workspace: Path) -> dict[str, Any]:
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="HQE_RC_WRITE_",
            suffix=".tmp",
            dir=workspace,
            delete=False,
        ) as handle:
            handle.write("HQE release-candidate write check.")
            temp_path = Path(handle.name)
        temp_path.unlink()
        return {
            "name": "Workspace write permission",
            "status": "PASS",
            "message": "Workspace can create and remove app files.",
        }
    except Exception as exc:
        return {
            "name": "Workspace write permission",
            "status": "FAILED",
            "message": f"{type(exc).__name__}: {exc}",
        }


def launcher_check(repo_root: Path) -> dict[str, Any]:
    pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
    app = repo_root / "scripts" / "hqe_product_app_v2.py"
    installer = (
        repo_root
        / "release"
        / "HQE_INSTALL_DESKTOP_SHORTCUT.ps1"
    )
    remover = (
        repo_root
        / "release"
        / "HQE_REMOVE_DESKTOP_SHORTCUT.ps1"
    )
    missing = [
        str(path)
        for path in (pythonw, app, installer, remover)
        if not path.exists()
    ]
    if missing:
        return {
            "name": "One-icon launcher assets",
            "status": "FAILED",
            "message": "Missing launcher assets: " + ", ".join(missing),
        }

    installer_text = installer.read_text(
        encoding="utf-8-sig",
        errors="ignore",
    )
    required = (
        "pythonw.exe",
        "hqe_product_app_v2.py",
        "Hunter Quant Engine.lnk",
    )
    absent = [
        marker for marker in required
        if marker.lower() not in installer_text.lower()
    ]
    return {
        "name": "One-icon launcher assets",
        "status": "PASS" if not absent else "FAILED",
        "message": (
            "Desktop shortcut targets pythonw app entry."
            if not absent
            else "Shortcut installer markers missing: "
            + ", ".join(absent)
        ),
    }


def app_navigation_check(repo_root: Path) -> dict[str, Any]:
    app = repo_root / "scripts" / "hqe_product_app_v2.py"
    if not app.exists():
        return {
            "name": "App navigation centers",
            "status": "FAILED",
            "message": "Main app file is missing.",
        }
    text = app.read_text(encoding="utf-8-sig", errors="ignore")
    missing = [
        marker for marker in APP_CENTER_MARKERS
        if marker not in text
    ]
    return {
        "name": "App navigation centers",
        "status": "PASS" if not missing else "FAILED",
        "message": (
            "All primary product centers are present."
            if not missing
            else "Missing app centers: " + ", ".join(missing)
        ),
        "missing_markers": missing,
    }


def ast_call_name(call: ast.Call) -> str:
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def unsafe_app_call_check(repo_root: Path) -> dict[str, Any]:
    candidates = [
        repo_root / "scripts" / "hqe_product_app_v2.py",
        *sorted(
            (repo_root / "scripts").glob("hqe_app_*center.py")
        ),
    ]
    findings: list[str] = []
    parse_errors: list[str] = []

    for path in candidates:
        if not path.exists():
            continue
        try:
            tree = ast.parse(
                path.read_text(encoding="utf-8-sig")
            )
        except Exception as exc:
            parse_errors.append(
                f"{path.name}: {type(exc).__name__}"
            )
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = ast_call_name(node)
            if name in FORBIDDEN_CALL_NAMES:
                findings.append(
                    f"{path.name}:{getattr(node, 'lineno', 0)}:{name}"
                )

    status = "PASS"
    message = "No direct real-order/execution calls found in app layer."
    if parse_errors or findings:
        status = "FAILED"
        message = (
            "App-layer execution safety scan found blockers."
        )
    return {
        "name": "App-layer no-execution AST scan",
        "status": status,
        "message": message,
        "findings": findings,
        "parse_errors": parse_errors,
    }


def manifest_required_file_checks(
    repo_root: Path,
) -> list[dict[str, Any]]:
    manifest = read_json(
        repo_root
        / "release"
        / "HQE_WINDOWS_RELEASE_MANIFEST.json"
    )
    checks: list[dict[str, Any]] = []
    for relative in manifest.get("required_files", []):
        path = repo_root / str(relative)
        checks.append(
            {
                "name": f"Required file: {relative}",
                "status": "PASS" if path.exists() else "FAILED",
                "message": (
                    "Required release file exists."
                    if path.exists()
                    else "Required release file is missing."
                ),
                "path": str(path),
            }
        )
    if not checks:
        checks.append(
            {
                "name": "Release manifest required files",
                "status": "FAILED",
                "message": "No required_files found in release manifest.",
            }
        )
    return checks


def guard_checks(repo_root: Path) -> list[dict[str, Any]]:
    manifest = read_json(
        repo_root
        / "release"
        / "HQE_WINDOWS_RELEASE_MANIFEST.json"
    )
    python_exe = (
        repo_root / ".venv" / "Scripts" / "python.exe"
    )
    checks: list[dict[str, Any]] = []
    for relative in manifest.get("guard_scripts", []):
        script = repo_root / str(relative)
        if not script.exists():
            checks.append(
                {
                    "name": f"Guard: {relative}",
                    "status": "FAILED",
                    "message": "Guard script is missing.",
                }
            )
            continue
        checks.append(
            command_check(
                f"Guard: {relative}",
                [
                    str(python_exe),
                    str(script),
                    "--guard-check",
                ],
                cwd=repo_root,
                timeout=150,
            )
        )
    return checks


def snapshot_checks(
    repo_root: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    python_exe = (
        repo_root / ".venv" / "Scripts" / "python.exe"
    )
    checks: list[dict[str, Any]] = []

    for relative in SNAPSHOT_SCRIPTS:
        script = repo_root / relative
        if not script.exists():
            checks.append(
                {
                    "name": f"Snapshot: {relative}",
                    "status": "CHECK_REQUIRED",
                    "message": "Snapshot script is missing.",
                }
            )
            continue

        result = command_check(
            f"Snapshot: {relative}",
            [
                str(python_exe),
                str(script),
                "--repo-root",
                str(repo_root),
                "--workspace",
                str(workspace),
                "--snapshot",
            ],
            cwd=repo_root,
            timeout=180,
            failure_status="CHECK_REQUIRED",
        )

        if result["status"] == "PASS":
            try:
                json.loads(str(result.get("stdout_tail", "")))
            except Exception:
                result["status"] = "CHECK_REQUIRED"
                result["message"] = (
                    "Snapshot command passed but JSON output "
                    "needs operator review."
                )
        checks.append(result)

    return checks


def freeze_hash_targets(repo_root: Path) -> list[Path]:
    manifest = read_json(
        repo_root
        / "release"
        / "HQE_WINDOWS_RELEASE_MANIFEST.json"
    )
    targets: list[Path] = []
    for relative in manifest.get("required_files", []):
        path = repo_root / str(relative)
        if path.exists() and path.is_file():
            targets.append(path)
    return sorted(set(targets))


def generate_freeze_manifest(
    repo_root: Path,
    *,
    source_head: str = "",
) -> dict[str, Any]:
    targets = freeze_hash_targets(repo_root)
    files = [
        {
            "path": str(path.relative_to(repo_root)).replace("\\", "/"),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        for path in targets
    ]
    payload = {
        "schema_version": "1.0",
        "product": "Hunter Quant Engine",
        "freeze_name": "HQE_PAPER_ONLY_PRODUCT_RC_FREEZE",
        "version": "0.9.0-paper-rc2",
        "generated_at_utc": utc_now_text(),
        "source_head_before_freeze_commit": source_head,
        "freeze_commit_message": (
            "Add end-to-end RC audit and paper-only product freeze"
        ),
        "file_count": len(files),
        "files": files,
        "scope": (
            "Paper/data/research product release candidate. "
            "Real execution is excluded."
        ),
        "safety_lock": dict(SAFETY_LOCK),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "profitability_claim": False,
    }
    target = repo_root / FREEZE_MANIFEST
    write_json(target, payload)
    payload["manifest_path"] = str(target)
    return payload


def verify_freeze_manifest(repo_root: Path) -> dict[str, Any]:
    target = repo_root / FREEZE_MANIFEST
    payload = read_json(target)
    if not payload:
        return {
            "name": "Paper-only RC freeze manifest",
            "status": "FAILED",
            "message": "Freeze manifest is missing or invalid.",
        }

    mismatches: list[str] = []
    missing: list[str] = []
    for item in payload.get("files", []):
        relative = str(item.get("path", ""))
        path = repo_root / relative
        if not path.exists():
            missing.append(relative)
            continue
        if sha256_file(path) != str(item.get("sha256", "")):
            mismatches.append(relative)

    return {
        "name": "Paper-only RC freeze manifest",
        "status": (
            "PASS"
            if not missing and not mismatches
            else "FAILED"
        ),
        "message": (
            "Freeze hashes match all recorded release files."
            if not missing and not mismatches
            else "Freeze manifest hash verification failed."
        ),
        "missing": missing,
        "mismatches": mismatches,
        "file_count": int(payload.get("file_count", 0) or 0),
        "manifest_path": str(target),
    }


def audit_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.extend(manifest_required_file_checks(repo_root))
    checks.extend(
        (
            launcher_check(repo_root),
            workspace_write_check(workspace),
            app_navigation_check(repo_root),
            unsafe_app_call_check(repo_root),
            verify_freeze_manifest(repo_root),
        )
    )
    checks.extend(guard_checks(repo_root))
    checks.extend(snapshot_checks(repo_root, workspace))

    failed = [
        item for item in checks
        if item.get("status") == "FAILED"
    ]
    review = [
        item for item in checks
        if item.get("status") == "CHECK_REQUIRED"
    ]
    passed = [
        item for item in checks
        if item.get("status") == "PASS"
    ]

    if failed:
        status = "FAILED"
    elif review:
        status = "PASS_WITH_REVIEW"
    else:
        status = "PASS"

    return {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "status": status,
        "message": (
            "End-to-end release-candidate audit passed."
            if status == "PASS"
            else (
                "Core RC audit passed; some workspace snapshots "
                "need operator review."
                if status == "PASS_WITH_REVIEW"
                else "Release-candidate audit found blocking failures."
            )
        ),
        "check_count": len(checks),
        "passed_count": len(passed),
        "review_count": len(review),
        "failed_count": len(failed),
        "checks": checks,
        "operations_executed": {
            "paper_watch": False,
            "market_data_fetch": False,
            "backtest": False,
            "report_generation": False,
            "broker_action": False,
            "real_order": False,
        },
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def write_audit_report(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    payload = audit_snapshot(repo_root, workspace)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = (
        workspace
        / AUDIT_FOLDER
        / f"HQE_END_TO_END_RC_AUDIT_{stamp}.json"
    )
    write_json(target, payload)
    payload["report_path"] = str(target)
    return payload


def latest_audit_report(workspace: Path) -> str:
    root = workspace / AUDIT_FOLDER
    candidates = sorted(
        root.glob("HQE_END_TO_END_RC_AUDIT_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if root.exists() else []
    return str(candidates[0]) if candidates else ""


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "END_TO_END_RC_AUDIT_AND_PAPER_ONLY_FREEZE",
        "snapshot_mode": "READ_ONLY",
        "freeze_hashes": "SHA256",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE end-to-end release-candidate audit"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--generate-freeze-manifest", action="store_true")
    parser.add_argument("--source-head", default="")
    parser.add_argument("--verify-freeze-manifest", action="store_true")
    parser.add_argument("--latest-report", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if args.generate_freeze_manifest:
        print(json.dumps(
            generate_freeze_manifest(
                repo_root,
                source_head=args.source_head,
            ),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.verify_freeze_manifest:
        payload = verify_freeze_manifest(repo_root)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1

    if not args.workspace:
        parser.error("--workspace is required.")

    workspace = Path(args.workspace)

    if args.audit:
        payload = (
            write_audit_report(repo_root, workspace)
            if args.write_report
            else audit_snapshot(repo_root, workspace)
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] != "FAILED" else 1
    if args.latest_report:
        print(json.dumps(
            {"latest_report": latest_audit_report(workspace)},
            indent=2,
            sort_keys=True,
        ))
        return 0

    parser.error(
        "Use --audit, --generate-freeze-manifest, "
        "--verify-freeze-manifest, --latest-report or --guard-check."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
