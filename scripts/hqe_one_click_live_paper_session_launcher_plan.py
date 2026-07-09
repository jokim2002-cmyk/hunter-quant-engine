from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from hqe_live_paper_ops_172_180_common import add_common_cli, as_path, base_payload, create_cmd, guard_payload, print_payload, write_outputs

MODULE_NUMBER = 177
MODULE_NAME = "One-Click Live Paper Session Launcher Plan"
BASENAME = "MODULE_177_ONE_CLICK_LIVE_PAPER_SESSION_LAUNCHER_PLAN_STATUS"


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = as_path(args.workspace)
    launcher = workspace / "RUN_HQE_ONE_CLICK_LIVE_PAPER_SESSION_PLAN_SAFE.cmd"
    payload = base_payload(MODULE_NUMBER, MODULE_NAME, workspace, args.trading_date, args.day_number)
    payload.update({
        "session_launcher_plan_status": "PASS",
        "decision": "ONE_CLICK_LIVE_PAPER_SESSION_PLAN_READY_MANUAL_OPERATOR_START_REQUIRED",
        "launcher_path": str(launcher),
        "manual_login_required": True,
        "auto_start_trading": False,
        "auto_broker_connect": False,
        "planned_steps": [
            "check login status",
            "run Fyers credential preflight",
            "run Fyers token offline check",
            "run symbol config guard",
            "optional explicit data-only LTP test",
            "optional explicit data-only 5m candle fetch",
            "run final readiness pack",
        ],
        "external_api_calls_executed_by_module_177": False,
        "order_api_invoked_by_module_177": False,
        "broker_execution_invoked_by_module_177": False,
        "auto_trading_started_by_module_177": False,
        "fake_trades_created_by_module_177": False,
    })
    if args.write:
        create_cmd(launcher, [
            f'cd /d "{Path.cwd()}"',
            'echo HQE ONE CLICK LIVE PAPER SESSION PLAN - SAFE',
            'echo No orders. No broker execution. No auto trading.',
            f'"{Path.cwd()}\\.venv\\Scripts\\python.exe" scripts\\hqe_local_login_shell.py --status --workspace "{workspace}"',
            f'"{Path.cwd()}\\.venv\\Scripts\\python.exe" scripts\\hqe_fyers_data_only_secret_preflight_pack.py --workspace "{workspace}" --write',
            f'"{Path.cwd()}\\.venv\\Scripts\\python.exe" scripts\\hqe_fyers_access_token_validation_pack.py --workspace "{workspace}" --write',
            f'"{Path.cwd()}\\.venv\\Scripts\\python.exe" scripts\\hqe_live_data_symbol_config_guard.py --workspace "{workspace}" --symbol "{args.symbol}" --write',
            f'"{Path.cwd()}\\.venv\\Scripts\\python.exe" scripts\\hqe_live_paper_operations_final_readiness_pack.py --workspace "{workspace}" --symbol "{args.symbol}" --write',
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
