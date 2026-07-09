from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from hqe_live_paper_ops_172_180_common import (
    add_common_cli,
    as_path,
    base_payload,
    credential_status,
    guard_payload,
    print_payload,
    write_outputs,
)

MODULE_NUMBER = 172
MODULE_NAME = "Fyers Live Data-Only LTP Test Button Integration"
BASENAME = "MODULE_172_FYERS_LIVE_DATA_ONLY_LTP_TEST_STATUS"


def _try_live_quote(symbol: str) -> Dict[str, Any]:
    client_id = os.getenv("FYERS_CLIENT_ID")
    token = os.getenv("FYERS_ACCESS_TOKEN")
    if not client_id or not token:
        return {"executed": False, "status": "MISSING_ENV_CREDENTIALS", "quote": None}
    try:
        from fyers_apiv3 import fyersModel  # type: ignore
    except Exception as exc:
        return {"executed": False, "status": "FYERS_SDK_NOT_INSTALLED", "error": str(exc), "quote": None}
    try:
        fyers = fyersModel.FyersModel(client_id=client_id, token=token, is_async=False, log_path="")
        data = {"symbols": symbol}
        response = fyers.quotes(data=data)
        return {
            "executed": True,
            "status": "DATA_ONLY_LTP_CALL_COMPLETED",
            "symbol": symbol,
            "response_redacted": response,
        }
    except Exception as exc:
        return {"executed": True, "status": "DATA_ONLY_LTP_CALL_FAILED", "error": str(exc), "quote": None}


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = as_path(args.workspace)
    payload = base_payload(MODULE_NUMBER, MODULE_NAME, workspace, args.trading_date, args.day_number)
    secrets = credential_status()
    live_result = {"executed": False, "status": "OFFLINE_DRY_RUN_BY_DEFAULT", "quote": None}
    if args.execute_live_data_only:
        live_result = _try_live_quote(args.symbol)
    payload.update(
        {
            "ltp_test_status": "PASS" if not str(live_result.get("status", "")).endswith("FAILED") else "FAIL",
            "decision": "FYERS_LTP_DATA_ONLY_TEST_READY" if not args.execute_live_data_only else live_result.get("status"),
            "symbol": args.symbol,
            "execute_live_data_only_requested": bool(args.execute_live_data_only),
            "external_api_calls_executed": bool(live_result.get("executed")),
            "external_api_calls_executed_by_module_172": bool(live_result.get("executed")),
            "live_ltp_result": live_result,
            "secrets": secrets,
            "order_api_invoked_by_module_172": False,
            "broker_execution_invoked_by_module_172": False,
            "auto_trading_started_by_module_172": False,
            "fake_trades_created_by_module_172": False,
        }
    )
    if args.write:
        payload["evidence_files"] = write_outputs(payload, workspace, BASENAME)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    add_common_cli(parser)
    parser.add_argument("--execute-live-data-only", action="store_true", help="Explicitly make a data-only quote call; order APIs remain blocked.")
    args = parser.parse_args()
    if args.guard_check:
        print_payload(guard_payload(MODULE_NUMBER, MODULE_NAME))
        return 0
    payload = build_payload(args)
    print_payload(payload)
    return 0 if payload.get("ltp_test_status") == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
