from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


KNOWN_TEMP_ARTIFACTS = (
    "HQE.spec",
    "build",
    "fix_broker.py",
    "hqe_analysis.txt",
    "profile.stats",
    "scripts/hqe_product_app_v2_backup.py",
    "scripts/hqe_product_app_v2_backup2.py",
)


def git_output(repo: Path, args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def workspace_preflight(repo: Path) -> dict[str, Any]:
    branch = git_output(repo, ["branch", "--show-current"])
    head = git_output(repo, ["rev-parse", "--short", "HEAD"])
    status = git_output(repo, ["status", "--porcelain"])
    remaining_temp = [
        relative
        for relative in KNOWN_TEMP_ARTIFACTS
        if (repo / relative).exists()
    ]
    status_lines = [line for line in status.splitlines() if line.strip()]
    allowed_changes = (
        ".gitignore",
        "docs/HQE_CURRENT_STATUS.md",
        "docs/HQE_MASTER_PRODUCT_ROADMAP.md",
        "release/HQE_INSTALL_DESKTOP_SHORTCUT.ps1",
        "release/HQE_PAPER_ONLY_RC_FREEZE_MANIFEST.json",
        "scripts/hqe_desktop_exe_launcher.py",
        "scripts/hqe_product_app_v2.py",
        "scripts/hqe_app_v2_ui_readiness_gate.py",
        "scripts/hqe_trader_report_renderer.py",
        "scripts/hqe_smc_live_direction.py",
        "scripts/run_forward_intraday_paper_supervisor.py",
        "tests/test_hqe_smc_live_direction_bridge.py",
        "scripts/hqe_current_day_session_guard.py",
        "tests/test_hqe_current_day_session_guard.py",
        "scripts/hqe_fyers_option_chain_data_only.py",
        "tests/test_hqe_fyers_option_chain_data_only.py",
        "tests/test_hqe_visible_fyers_auth_button.py",
        "scripts/hqe_fyers_selected_option_history_data_only.py",
        "tests/test_hqe_fyers_selected_option_history_data_only.py",
        "scripts/hqe_current_day_recorded_replay_evaluation.py",
        "tests/test_hqe_current_day_recorded_replay_evaluation.py",
        "scripts/hqe_recorded_replay_today_report.py",
        "tests/test_hqe_recorded_replay_today_report.py",
        "scripts/hqe_automatic_daily_current_day_workflow.py",
        "tests/test_hqe_automatic_daily_current_day_workflow.py",
        "scripts/hqe_paper_watch_auth_readiness_gate.py",
        "tests/test_hqe_paper_watch_auth_readiness_gate.py",
        "scripts/hqe_app_fyers_auth.py",
        "tests/test_hqe_fyers_auth_exchange_diagnostics.py",
        "tests/test_hqe_expiry_day_next_week_selection.py",
        "tests/test_hqe_paper_watch_ready_card_truth.py",
        "scripts/hqe_release_workspace_preflight.py",
        "scripts/hqe_windows_release_builder.py",
        "tests/test_hqe_release_workspace_preflight.py",
        "tests/test_hqe_overview_centered_actions.py",
        "tests/test_hqe_broker_connect_scrollbar.py",
        "tests/test_hqe_app_daily_close_center.py",
        "tests/test_hqe_app_daily_operations.py",
        "tests/test_hqe_app_v2_navigation_operations.py",
        "tests/test_hqe_trader_report_renderer.py",
        "tests/test_hqe_final_rich_overview_ui.py",
        "tests/test_hqe_windows_release_builder.py",
    )
    unexpected = [
        line
        for line in status_lines
        if not any(line.endswith(path) for path in allowed_changes)
    ]
    passed = branch == "master" and not remaining_temp and not unexpected
    return {
        "status": "PASS" if passed else "FAILED",
        "branch": branch,
        "head": head,
        "remaining_temp_artifacts": remaining_temp,
        "unexpected_git_changes": unexpected,
        "git_status": status_lines,
        "real_order_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_invoked": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HQE release workspace preflight")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = workspace_preflight(Path(args.repo_root))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"HQE RELEASE WORKSPACE PREFLIGHT: {payload['status']}")
        print(f"Branch: {payload['branch']}")
        print(f"HEAD: {payload['head']}")
        print(f"Unexpected changes: {len(payload['unexpected_git_changes'])}")
        print(f"Remaining temp artifacts: {len(payload['remaining_temp_artifacts'])}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
