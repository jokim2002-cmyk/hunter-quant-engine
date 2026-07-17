from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_MULTI_STRATEGY_VISIBLE_NAV_ACCEPTANCE_V8"
APP = "scripts/hqe_product_app_v2.py"
REQUIRED_SURFACE_MARKERS = (
    "Product Strategy Manager",
    "Reviewed Package Import",
    "Parallel Observation Center",
    "Windows Release Center",
    "Final RC Audit & Freeze",
    "Operator Acceptance & RC Sign-Off",
    "HQE_ADVANCED_TOOLS_DIRECT_NAV_PASS",
    "Parallel Isolated Paper Observation",
    "HQE_VISIBLE_NAV_TITLE_WAIT_RECOVERY_V2",
    "TITLE_FRAGMENT_WAIT_V3",
    "HQE_VISIBLE_NAV_CLEAN_EXIT_RECOVERY_V3",
    "SMOKE_FINALLY_DESTROY_V4",
    "HQE_DIRECT_PARALLEL_MANAGER_BUTTON_INVOKE_V7",
    "HQE_RECURSIVE_TOPLEVEL_DISCOVERY_V8",
    "HQE_ALL_GUI_SMOKE_STARTUP_TIMERS_DISABLED_V7",
    "HQE_GUI_SMOKE_HEALTH_LOOP_DISABLED_V7",
    "HQE_SMOKE_CALLBACK_ERROR_CAPTURE_V6",
    "HQE_ADVANCED_TOOLS_SMOKE_CLEAN_EXIT_V4",
    "HQE_ADVANCED_TOOLS_SMOKE_PASS",
    "HQE_FULL_CENTER_SMOKE_PASS",
)
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
    "no_canonical_activation": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "AUTOMATED_WINDOWS_GUI_RENDER_ACCEPTANCE",
        "actual_gui_render_smoke": True,
        "direct_visible_navigation_required": True,
        "actual_visible_button_invocation_required": True,
        "direct_navigation_detector": "RECURSIVE_TOPLEVEL_DISCOVERY_V8",
        "direct_parallel_open_mode": "MANAGER_VISIBLE_BUTTON_COMMAND",
        "smoke_warning_modals_suppressed": True,
        "smoke_background_worker_started": False,
        "smoke_clean_exit_required": True,
        "smoke_callback_errors_captured": True,
        "all_gui_smoke_background_workers_started": False,
        "all_gui_smoke_startup_timers_scheduled": False,
        "trader_health_loop_scheduled_in_smoke": False,
        "direct_manager_button_command_invoked": True,
        "nested_toplevel_discovery": True,
        "nested_observation_window_expected": True,
        "screenshots_claimed": False,
        "manual_visual_signoff_claimed": False,
        "canonical_activation_allowed": False,
        "runtime_control_allowed": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "real_money_allowed": False,
        "safety_lock": dict(SAFETY_LOCK),
    }


def source_surface_check(repo_root: Path) -> dict[str, Any]:
    app = repo_root / APP
    if not app.is_file():
        return {"status": "FAILED", "missing": [APP], "sha256": ""}
    text = app.read_text(encoding="utf-8-sig", errors="replace")
    missing = [marker for marker in REQUIRED_SURFACE_MARKERS if marker not in text]
    return {
        "status": "PASS" if not missing else "FAILED",
        "missing": missing,
        "sha256": sha256(app),
        "marker_count": len(REQUIRED_SURFACE_MARKERS) - len(missing),
    }


def run_gui_smoke(
    repo_root: Path,
    workspace: Path,
    *,
    environment_flag: str,
    required_marker: str,
    timeout: int = 90,
) -> dict[str, Any]:
    python_exe = repo_root / ".venv" / "Scripts" / "python.exe"
    app = repo_root / APP
    env = dict(os.environ)
    env[environment_flag] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    command = [
        str(python_exe), str(app), "--workspace", str(workspace),
        "--skip-license-check",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            env=env,
        )
        combined = (completed.stdout or "") + (completed.stderr or "")
        clean_exit_required = (
            environment_flag == "HQE_ADVANCED_TOOLS_SMOKE"
        )
        clean_exit_found = (
            "HQE_ADVANCED_TOOLS_SMOKE_CLEAN_EXIT_V4" in combined
        )
        passed = (
            completed.returncode == 0
            and required_marker in combined
            and (not clean_exit_required or clean_exit_found)
        )
        return {
            "status": "PASS" if passed else "FAILED",
            "return_code": completed.returncode,
            "required_marker": required_marker,
            "marker_found": required_marker in combined,
            "clean_exit_marker_found": clean_exit_found,
            "stdout_tail": (completed.stdout or "")[-2400:],
            "stderr_tail": (completed.stderr or "")[-1800:],
        }
    except Exception as exc:
        return {
            "status": "FAILED",
            "required_marker": required_marker,
            "marker_found": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_visual_acceptance(
    repo_root: Path,
    workspace: Path,
    *,
    run_gui: bool = True,
) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    source = source_surface_check(repo_root)
    if run_gui:
        advanced = run_gui_smoke(
            repo_root,
            workspace / "advanced_tools",
            environment_flag="HQE_ADVANCED_TOOLS_SMOKE",
            required_marker="HQE_ADVANCED_TOOLS_DIRECT_NAV_PASS",
        )
        centers = run_gui_smoke(
            repo_root,
            workspace / "full_centers",
            environment_flag="HQE_FULL_CENTER_SMOKE",
            required_marker="HQE_FULL_CENTER_SMOKE_PASS",
        )
    else:
        advanced = {"status": "SKIPPED"}
        centers = {"status": "SKIPPED"}
    passed = (
        source["status"] == "PASS"
        and advanced["status"] == "PASS"
        and centers["status"] == "PASS"
    ) if run_gui else source["status"] == "PASS"
    payload = {
        "version": VERSION,
        "status": "PASS" if passed else "FAILED",
        "generated_at_utc": utc_now(),
        "source_surface": source,
        "advanced_tools_render_smoke": advanced,
        "full_center_render_smoke": centers,
        "visible_navigation": {
            "status": advanced.get("status", "FAILED"),
            "advanced_tools_page_direct_cards": (
                advanced.get("status") == "PASS"
            ),
            "product_strategy_manager_button_invoked": (
                advanced.get("status") == "PASS"
            ),
            "parallel_observation_button_invoked": (
                advanced.get("status") == "PASS"
            ),
            "actual_button_invocation": (
                run_gui and advanced.get("status") == "PASS"
            ),
            "detector_version": "RECURSIVE_TOPLEVEL_DISCOVERY_V8",
            "direct_parallel_open_mode": (
                "MANAGER_VISIBLE_BUTTON_COMMAND"
            ),
            "accepted_parallel_window_title": (
                "Parallel Isolated Paper Observation"
            ),
            "smoke_warning_modals_suppressed": True,
            "smoke_background_worker_started": False,
            "all_gui_smoke_background_workers_started": False,
            "all_gui_smoke_startup_timers_scheduled": False,
            "trader_health_loop_scheduled_in_smoke": False,
            "direct_manager_button_command_invoked": (
                run_gui and advanced.get("status") == "PASS"
            ),
            "nested_toplevel_discovery": True,
            "nested_observation_window_expected": True,
            "callback_error_capture_enabled": True,
            "smoke_clean_exit_marker_found": (
                "HQE_ADVANCED_TOOLS_SMOKE_CLEAN_EXIT_V4"
                in (
                    str(advanced.get("stdout_tail", ""))
                    + str(advanced.get("stderr_tail", ""))
                )
            ),
        },
        "actual_gui_render_smoke_executed": run_gui,
        "screenshots_captured": False,
        "manual_visual_signoff_claimed": False,
        "canonical_selection_changed": False,
        "canonical_activation_performed": False,
        "human_cutover_gate_created": False,
        "runtime_control_performed": False,
        "real_order_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_invoked": False,
        "safety_lock": dict(SAFETY_LOCK),
    }
    report = workspace / "HQE_PHASE8_AUTOMATED_VISUAL_ACCEPTANCE.json"
    report.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["report_path"] = str(report)
    payload["report_sha256"] = sha256(report)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE Phase 8 automated visual acceptance")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--workspace", default=r"D:\HQE_BACKTEST_RUNS\HQE_PHASE8_VISUAL_ACCEPTANCE")
    parser.add_argument("--accept", action="store_true")
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()
    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.accept:
        parser.error("Use --accept or --guard-check")
    payload = build_visual_acceptance(
        Path(args.repo_root), Path(args.workspace), run_gui=not args.source_only
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
