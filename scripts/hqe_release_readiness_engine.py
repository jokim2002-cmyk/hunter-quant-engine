from __future__ import annotations

import argparse
import json
import os
import platform
import py_compile
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VERSION = "HQE_RELEASE_READINESS_ENGINE_V1"
CENTER_FOLDER = "HQE_RELEASE_CENTER"
OPERATION_FILE = "HQE_RELEASE_OPERATION_STATUS.json"

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
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


def center_paths(workspace: Path) -> dict[str, Path]:
    root = workspace / CENTER_FOLDER
    return {
        "root": root,
        "operation": root / OPERATION_FILE,
        "backups": root / "backups",
        "restore_staging": root / "restore_staging",
        "diagnostics": root / "diagnostics",
        "rc_reports": root / "rc_reports",
    }


def release_manifest(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "release" / "HQE_WINDOWS_RELEASE_MANIFEST.json"
    payload = read_json(path)
    payload["manifest_path"] = str(path)
    return payload


def check_required_files(
    repo_root: Path,
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for relative in manifest.get("required_files", []):
        path = repo_root / str(relative)
        checks.append(
            {
                "name": str(relative),
                "status": "PASS" if path.exists() else "FAILED",
                "path": str(path),
                "message": (
                    "Required file exists."
                    if path.exists()
                    else "Required file is missing."
                ),
            }
        )
    return checks


def run_guard_check(
    repo_root: Path,
    relative_script: str,
) -> dict[str, Any]:
    path = repo_root / relative_script
    if not path.exists():
        return {
            "name": relative_script,
            "status": "FAILED",
            "message": "Guard script is missing.",
        }

    completed = subprocess.run(
        [
            str(repo_root / ".venv" / "Scripts" / "python.exe"),
            str(path),
            "--guard-check",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "name": relative_script,
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "message": "Guard-check completed.",
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-700:],
        "stderr_tail": completed.stderr[-700:],
    }


def compile_app(repo_root: Path) -> dict[str, Any]:
    app = repo_root / "scripts" / "hqe_product_app_v2.py"
    try:
        py_compile.compile(
            str(app),
            doraise=True,
        )
        return {
            "name": "App Python compile",
            "status": "PASS",
            "message": "Main app compiles successfully.",
        }
    except Exception as exc:
        return {
            "name": "App Python compile",
            "status": "FAILED",
            "message": f"{type(exc).__name__}: {exc}",
        }


def license_check(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_license_lifecycle import license_snapshot

    snapshot = license_snapshot(repo_root, workspace)
    acceptable = snapshot.get("status") in {
        "DEVELOPMENT_MODE",
        "ACTIVE",
        "EXPIRING_SOON",
    }
    return {
        "name": "License lifecycle",
        "status": "PASS" if acceptable else "CHECK_REQUIRED",
        "message": str(snapshot.get("message", "")),
        "details": snapshot,
    }


def release_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    manifest = release_manifest(repo_root)
    required_checks = check_required_files(repo_root, manifest)
    license_status = license_check(repo_root, workspace)
    paths = center_paths(workspace)
    operation = read_json(paths["operation"])

    passed = sum(
        1
        for item in required_checks
        if item["status"] == "PASS"
    )
    failed = sum(
        1
        for item in required_checks
        if item["status"] != "PASS"
    )
    display = (
        f"Release Center: required files {passed}/"
        f"{len(required_checks)} | missing {failed} | "
        f"license {license_status['status']} | "
        f"operation {operation.get('status', 'IDLE')}"
    )
    return {
        "version": VERSION,
        "display_text": display,
        "manifest": manifest,
        "required_checks": required_checks,
        "license": license_status,
        "operation": operation,
        "paths": {
            key: str(value)
            for key, value in paths.items()
        },
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def safe_zip_member(name: str) -> bool:
    normalized = name.replace("\\", "/")
    path = Path(normalized)
    return not (
        path.is_absolute()
        or ".." in path.parts
        or normalized.startswith("/")
    )


def backup_candidates(workspace: Path) -> list[Path]:
    explicit = (
        workspace / "HQE_ACTIVE_STRATEGY_SELECTION.json",
        workspace / "HQE_LICENSE.json",
        workspace / "HQE_PAPER_VALIDATION_REPORT_STATUS.json",
        workspace / "HQE_APP_PAPER_WATCH_STATUS.json",
        workspace / "HQE_APP_SAFETY_AUDIT_STATUS.json",
    )
    paths = [
        path for path in explicit
        if path.exists() and path.is_file()
    ]
    strategy_root = workspace / "strategy_packs"
    if strategy_root.exists():
        paths.extend(
            path
            for path in strategy_root.rglob("*")
            if path.is_file()
        )
    return sorted(set(paths))


def create_backup(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    del repo_root
    paths = center_paths(workspace)
    paths["backups"].mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_path = paths["backups"] / f"HQE_USER_BACKUP_{stamp}.zip"

    candidates = backup_candidates(workspace)
    manifest = {
        "version": VERSION,
        "created_at_utc": utc_now_text(),
        "workspace": str(workspace),
        "file_count": len(candidates),
        "files": [
            str(path.relative_to(workspace)).replace("\\", "/")
            for path in candidates
        ],
        "restore_policy": "STAGING_ONLY_NO_OVERWRITE",
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
    }

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "HQE_BACKUP_MANIFEST.json",
            json.dumps(manifest, indent=2, sort_keys=True),
        )
        for path in candidates:
            archive.write(
                path,
                arcname=str(path.relative_to(workspace)).replace(
                    "\\",
                    "/",
                ),
            )

    return {
        "version": VERSION,
        "status": "PASS",
        "message": "HQE user backup created.",
        "backup_path": str(zip_path),
        "file_count": len(candidates),
        "completed_at_utc": utc_now_text(),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
    }


def stage_restore(
    repo_root: Path,
    workspace: Path,
    source_zip: Path,
) -> dict[str, Any]:
    del repo_root
    if not source_zip.exists():
        raise FileNotFoundError("Backup ZIP does not exist.")

    paths = center_paths(workspace)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    staging = paths["restore_staging"] / f"RESTORE_{stamp}"
    staging.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_zip, "r") as archive:
        unsafe = [
            info.filename
            for info in archive.infolist()
            if not safe_zip_member(info.filename)
        ]
        if unsafe:
            shutil.rmtree(staging, ignore_errors=True)
            raise ValueError(
                "Unsafe ZIP paths detected: " + ", ".join(unsafe)
            )
        archive.extractall(staging)

    manifest = read_json(staging / "HQE_BACKUP_MANIFEST.json")
    if not manifest:
        shutil.rmtree(staging, ignore_errors=True)
        raise ValueError("HQE backup manifest is missing or invalid.")

    return {
        "version": VERSION,
        "status": "PASS",
        "message": (
            "Backup extracted to restore staging. "
            "No live files were overwritten."
        ),
        "source_zip": str(source_zip),
        "staging_dir": str(staging),
        "manifest": manifest,
        "completed_at_utc": utc_now_text(),
        "overwrite_performed": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
    }


def safe_snapshot(
    name: str,
    callback,
) -> dict[str, Any]:
    try:
        payload = callback()
        return {
            "name": name,
            "status": "PASS",
            "payload": payload,
        }
    except Exception as exc:
        return {
            "name": name,
            "status": "UNAVAILABLE",
            "message": f"{type(exc).__name__}: {exc}",
        }


def git_head(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return completed.stdout.strip()
    except Exception:
        return ""


def create_diagnostics_bundle(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_app_market_data_quality_center import center_snapshot
    from hqe_app_operator_dashboard import operator_dashboard_snapshot
    from hqe_app_paper_validation_report_center import (
        paper_validation_center_snapshot,
    )
    from hqe_app_safety_evidence_center import safety_snapshot
    from hqe_app_strategy_builder_center import builder_center_snapshot

    paths = center_paths(workspace)
    paths["diagnostics"].mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    folder = paths["diagnostics"] / f"DIAGNOSTICS_{stamp}"
    folder.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "system": {
            "platform": platform.platform(),
            "python": sys.version,
            "machine": platform.machine(),
            "git_head": git_head(repo_root),
            "repo_root": str(repo_root),
            "workspace": str(workspace),
        },
        "release": release_snapshot(repo_root, workspace),
        "components": [
            safe_snapshot(
                "operator_dashboard",
                lambda: operator_dashboard_snapshot(
                    repo_root,
                    workspace,
                ),
            ),
            safe_snapshot(
                "market_data_quality",
                lambda: center_snapshot(repo_root, workspace),
            ),
            safe_snapshot(
                "strategy_builder",
                lambda: builder_center_snapshot(
                    repo_root,
                    workspace,
                ),
            ),
            safe_snapshot(
                "paper_validation",
                lambda: paper_validation_center_snapshot(
                    repo_root,
                    workspace,
                ),
            ),
            safe_snapshot(
                "safety",
                lambda: safety_snapshot(repo_root, workspace),
            ),
        ],
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }
    json_path = folder / "HQE_DIAGNOSTICS.json"
    write_json(json_path, payload)

    zip_path = folder / "HQE_DIAGNOSTICS_BUNDLE.zip"
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.write(json_path, arcname=json_path.name)

    return {
        "version": VERSION,
        "status": "PASS",
        "message": "HQE diagnostics bundle created.",
        "diagnostics_dir": str(folder),
        "json_path": str(json_path),
        "zip_path": str(zip_path),
        "completed_at_utc": utc_now_text(),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
    }


def run_rc_dry_run(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    paths = center_paths(workspace)
    paths["rc_reports"].mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = (
        paths["rc_reports"]
        / f"HQE_RELEASE_CANDIDATE_DRY_RUN_{stamp}.json"
    )

    manifest = release_manifest(repo_root)
    checks: list[dict[str, Any]] = []
    checks.extend(check_required_files(repo_root, manifest))
    checks.append(compile_app(repo_root))
    checks.append(license_check(repo_root, workspace))

    for script in manifest.get("guard_scripts", []):
        checks.append(run_guard_check(repo_root, str(script)))

    failed = [
        item
        for item in checks
        if item.get("status") == "FAILED"
    ]
    review = [
        item
        for item in checks
        if item.get("status") == "CHECK_REQUIRED"
    ]
    status = "PASS" if not failed else "FAILED"

    payload = {
        "version": VERSION,
        "status": status,
        "message": (
            "Release-candidate guard dry run passed."
            if status == "PASS"
            else "Release-candidate dry run found blocking failures."
        ),
        "generated_at_utc": utc_now_text(),
        "check_count": len(checks),
        "failed_count": len(failed),
        "review_count": len(review),
        "checks": checks,
        "report_path": str(report_path),
        "operations_executed": {
            "paper_watch": False,
            "market_data_fetch": False,
            "backtest": False,
            "report_generation": False,
            "broker_action": False,
            "real_order": False,
        },
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }
    write_json(report_path, payload)
    return payload


def latest_output_paths(workspace: Path) -> dict[str, str]:
    paths = center_paths(workspace)

    def latest(root: Path, pattern: str) -> str:
        values = sorted(
            root.glob(pattern),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        ) if root.exists() else []
        return str(values[0]) if values else ""

    return {
        "latest_backup": latest(paths["backups"], "*.zip"),
        "latest_restore_staging": latest(
            paths["restore_staging"],
            "RESTORE_*",
        ),
        "latest_diagnostics": latest(
            paths["diagnostics"],
            "DIAGNOSTICS_*",
        ),
        "latest_rc_report": latest(
            paths["rc_reports"],
            "*.json",
        ),
    }


def execute_operation(
    operation: str,
    repo_root: Path,
    workspace: Path,
    source_zip: str = "",
) -> dict[str, Any]:
    paths = center_paths(workspace)
    write_json(
        paths["operation"],
        {
            "version": VERSION,
            "status": "RUNNING",
            "operation": operation,
            "message": f"Release operation {operation} is running.",
            "started_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        },
    )

    if operation == "backup":
        result = create_backup(repo_root, workspace)
    elif operation == "restore_stage":
        result = stage_restore(
            repo_root,
            workspace,
            Path(source_zip),
        )
    elif operation == "diagnostics":
        result = create_diagnostics_bundle(repo_root, workspace)
    elif operation == "rc_dry_run":
        result = run_rc_dry_run(repo_root, workspace)
    else:
        raise ValueError("Unsupported release operation.")

    result["operation"] = operation
    write_json(paths["operation"], result)
    return result


def install_shortcut_command(
    repo_root: Path,
) -> list[str]:
    script = (
        repo_root
        / "release"
        / "HQE_INSTALL_DESKTOP_SHORTCUT.ps1"
    )
    if not script.exists():
        raise FileNotFoundError("Desktop shortcut installer is missing.")
    return [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]


def launch_shortcut_install(
    repo_root: Path,
) -> subprocess.Popen[Any]:
    return subprocess.Popen(
        install_shortcut_command(repo_root),
        cwd=repo_root,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "WINDOWS_RELEASE_HARDENING_AND_RC_DRY_RUN",
        "backup_restore_policy": "RESTORE_STAGING_ONLY_NO_OVERWRITE",
        "shortcut_target": "PYTHONW_APP",
        "dry_run_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE Windows release-readiness engine"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--operation", default="")
    parser.add_argument("--source-zip", default="")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")

    repo_root = Path(args.repo_root)
    workspace = Path(args.workspace)

    if args.snapshot:
        print(json.dumps(
            {
                **release_snapshot(repo_root, workspace),
                "latest_outputs": latest_output_paths(workspace),
            },
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.operation:
        payload = execute_operation(
            args.operation,
            repo_root,
            workspace,
            args.source_zip,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("status") == "PASS" else 1

    parser.error("Use --snapshot, --operation or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
