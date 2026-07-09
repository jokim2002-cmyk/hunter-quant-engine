from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from hqe_live_paper_ops_172_180_common import add_common_cli, as_path, base_payload, create_cmd, guard_payload, print_payload, write_outputs

MODULE_NUMBER = 179
MODULE_NAME = "Startup Shortcut Installer Review Pack"
BASENAME = "MODULE_179_STARTUP_SHORTCUT_INSTALLER_REVIEW_PACK_STATUS"


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = as_path(args.workspace)
    installer = workspace / "INSTALL_HQE_DASHBOARD_STARTUP_SHORTCUT_REVIEW_ONLY.cmd"
    dashboard_launcher = workspace / "OPEN_HQE_VISUAL_DASHBOARD_V2_LIVE_PAPER.cmd"
    payload = base_payload(MODULE_NUMBER, MODULE_NAME, workspace, args.trading_date, args.day_number)
    payload.update({
        "startup_installer_review_status": "PASS",
        "decision": "STARTUP_SHORTCUT_INSTALLER_REVIEW_READY_MANUAL_INSTALL_REQUIRED",
        "scheduled_task_installed_by_this_run": False,
        "startup_folder_modified_by_this_run": False,
        "installer_review_script_emitted": bool(args.write),
        "installer_review_path": str(installer),
        "dashboard_launcher_path": str(dashboard_launcher),
        "auto_start_trading": False,
        "auto_broker_connect": False,
        "external_api_calls_executed_by_module_179": False,
        "order_api_invoked_by_module_179": False,
        "broker_execution_invoked_by_module_179": False,
        "auto_trading_started_by_module_179": False,
        "fake_trades_created_by_module_179": False,
    })
    if args.write:
        create_cmd(installer, [
            'echo HQE STARTUP SHORTCUT REVIEW ONLY',
            'echo This file does not install automatically. Review before manual use.',
            f'echo Dashboard launcher: "{dashboard_launcher}"',
            'echo Safety: login gate only, no orders, no broker execution, no auto trading.',
        ])
        payload["evidence_files"] = write_outputs(payload, workspace, BASENAME)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    add_common_cli(parser)
    args = parser.parse_args()
    if args.guard_check:
        print_payload(guard_payload(MODULE_NUMBER, MODULE_NAME))
        return 0
    payload = build_payload(args)
    print_payload(payload)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
