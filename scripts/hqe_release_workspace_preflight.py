from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

VERSION = "HQE_RELEASE_WORKSPACE_PREFLIGHT_V2"
APPROVED_RELEASE_BRANCHES = (
    "master",
    "feature/hqe-multi-strategy-phase1",
)
KNOWN_TEMP_ARTIFACTS = (
    "HQE.spec", "build", "fix_broker.py", "hqe_analysis.txt", "profile.stats",
    "scripts/hqe_product_app_v2_backup.py",
    "scripts/hqe_product_app_v2_backup2.py",
)
PHASE8_ALLOWED_CHANGES = (
    "docs/HQE_CURRENT_STATUS.md",
    "docs/HQE_MASTER_HANDOVER_PROMPT.md",
    "docs/HQE_MULTI_STRATEGY_ROADMAP.md",
    "docs/HQE_MULTI_STRATEGY_PHASE8_FINAL_RELEASE_CLOSURE.md",
    "release/HQE_WINDOWS_RELEASE_MANIFEST.json",
    "release/HQE_PAPER_ONLY_RC_FREEZE_MANIFEST.json",
    "release/HQE_MULTI_STRATEGY_PHASE8_RELEASE_CLOSURE.json",
    "scripts/hqe_release_candidate_audit.py",
    "scripts/hqe_release_workspace_preflight.py",
    "scripts/hqe_final_release_qa.py",
    "scripts/hqe_multi_strategy_phase8_visual_acceptance.py",
    "scripts/hqe_multi_strategy_phase8_release_closure.py",
    "tests/test_hqe_release_candidate_audit.py",
    "tests/test_hqe_release_workspace_preflight.py",
    "tests/test_hqe_final_release_qa.py",
    "tests/test_hqe_multi_strategy_phase8_release_closure.py",
    "tests/test_hqe_multi_strategy_phase8_release_wiring.py",
)
LEGACY_ALLOWED_CHANGES = (
    ".gitignore", "docs/HQE_MASTER_PRODUCT_ROADMAP.md",
    "release/HQE_INSTALL_DESKTOP_SHORTCUT.ps1",
    "scripts/hqe_desktop_exe_launcher.py", "scripts/hqe_product_app_v2.py",
    "scripts/hqe_app_v2_ui_readiness_gate.py", "scripts/hqe_trader_report_renderer.py",
    "scripts/hqe_smc_live_direction.py", "scripts/run_forward_intraday_paper_supervisor.py",
    "docs/HQE_PAPER_ONLY_RC_OPERATOR_GUIDE.md", "scripts/hqe_windows_release_builder.py",
)
ALLOWED_CHANGES = tuple(dict.fromkeys(PHASE8_ALLOWED_CHANGES + LEGACY_ALLOWED_CHANGES))


def git_output(repo: Path, args: list[str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


def workspace_preflight(repo: Path) -> dict[str, Any]:
    branch = git_output(repo, ["branch", "--show-current"])
    head = git_output(repo, ["rev-parse", "--short", "HEAD"])
    status = git_output(repo, ["status", "--porcelain", "--untracked-files=all"])
    remaining_temp = [relative for relative in KNOWN_TEMP_ARTIFACTS if (repo / relative).exists()]
    status_lines = [line for line in status.splitlines() if line.strip()]
    unexpected = [
        line for line in status_lines
        if not any(line.replace("\\", "/").endswith(path) for path in ALLOWED_CHANGES)
    ]
    forbidden = [
        line for line in status_lines
        if any(token in line.lower() for token in ("private_key", "owner_private"))
        or line.lower().endswith(".key")
    ]
    branch_allowed = branch in APPROVED_RELEASE_BRANCHES
    passed = branch_allowed and not remaining_temp and not unexpected and not forbidden
    return {
        "version": VERSION,
        "status": "PASS" if passed else "FAILED",
        "branch": branch,
        "branch_allowed": branch_allowed,
        "release_mode": "MASTER_RELEASE" if branch == "master" else "CONTROLLED_FEATURE_RELEASE",
        "head": head,
        "remaining_temp_artifacts": remaining_temp,
        "unexpected_git_changes": unexpected,
        "forbidden_key_changes": forbidden,
        "git_status": status_lines,
        "allowed_change_count": len(ALLOWED_CHANGES),
        "real_order_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_invoked": False,
        "canonical_activation_invoked": False,
        "master_merge_invoked": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HQE release workspace preflight")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.guard_check:
        print(json.dumps({
            "version": VERSION, "guard_check_status": "PASS",
            "approved_release_branches": list(APPROVED_RELEASE_BRANCHES),
            "real_orders_allowed": False, "broker_execution_allowed": False,
            "canonical_activation_allowed": False, "master_merge_allowed": False,
        }, indent=2, sort_keys=True))
        return 0
    payload = workspace_preflight(Path(args.repo_root))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"HQE RELEASE WORKSPACE PREFLIGHT: {payload['status']}")
        print(f"Branch: {payload['branch']}")
        print(f"Mode: {payload['release_mode']}")
        print(f"Unexpected changes: {len(payload['unexpected_git_changes'])}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
