from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from hqe_live_paper_ops_172_180_common import add_common_cli, as_path, base_payload, credential_status, guard_payload, print_payload, write_outputs

MODULE_NUMBER = 180
MODULE_NAME = "Live Paper Operations Final Readiness Pack"
BASENAME = "MODULE_180_LIVE_PAPER_OPERATIONS_FINAL_READINESS_STATUS"

EXPECTED = [
    "MODULE_172_FYERS_LIVE_DATA_ONLY_LTP_TEST_STATUS.json",
    "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json",
    "MODULE_174_LIVE_DATA_SYMBOL_CONFIG_GUARD_STATUS.json",
    "MODULE_175_NEXT_PAPER_SESSION_DAY_GENERATOR_STATUS.json",
    "MODULE_176_LOCAL_VISUAL_DASHBOARD_LIVE_PAPER_V2_STATUS.json",
    "MODULE_177_ONE_CLICK_LIVE_PAPER_SESSION_LAUNCHER_PLAN_STATUS.json",
    "MODULE_178_LIVE_PAPER_REPORT_INDEX_V2_STATUS.json",
    "MODULE_179_STARTUP_SHORTCUT_INSTALLER_REVIEW_PACK_STATUS.json",
]


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = as_path(args.workspace)
    existing = [str(workspace / name) for name in EXPECTED if (workspace / name).exists()]
    missing = [name for name in EXPECTED if not (workspace / name).exists()]
    secrets = credential_status()
    ready = not missing and secrets["credentials_complete_for_future_data_transport"]
    payload = base_payload(MODULE_NUMBER, MODULE_NAME, workspace, args.trading_date, args.day_number)
    payload.update({
        "live_paper_operations_final_readiness_status": "PASS" if ready else "PARTIAL",
        "decision": "LIVE_PAPER_OPERATIONS_READY_FOR_MANUAL_MARKET_DAY_USE" if ready else "LIVE_PAPER_OPERATIONS_PARTIAL_RUN_MODULES_172_179_FIRST",
        "expected_status_files_count": len(EXPECTED),
        "existing_status_files_count": len(existing),
        "existing_status_files": existing,
        "missing_status_files": missing,
        "secrets": secrets,
        "ready_for_daily_paper_validation_operation": ready,
        "ready_for_real_money": False,
        "real_money_requires_future_explicit_manual_approval": True,
        "target_valid_paper_trade_days": 30,
        "external_api_calls_executed_by_module_180": False,
        "order_api_invoked_by_module_180": False,
        "broker_execution_invoked_by_module_180": False,
        "auto_trading_started_by_module_180": False,
        "fake_trades_created_by_module_180": False,
    })
    if args.write:
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
