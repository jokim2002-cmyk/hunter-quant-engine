from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime
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

MODULE_NUMBER = 173
MODULE_NAME = "Fyers Historical 5m Candle Data-Only Fetcher"
BASENAME = "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS"


def write_sample_candles(workspace: Path, trading_date: str) -> str:
    path = workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["datetime", "open", "high", "low", "close", "volume", "source"])
        writer.writeheader()
        writer.writerow({
            "datetime": f"{trading_date}T09:15:00",
            "open": "",
            "high": "",
            "low": "",
            "close": "",
            "volume": "",
            "source": "sample_schema_no_live_api_call_by_default",
        })
    return str(path)


def _try_history(symbol: str, trading_date: str) -> Dict[str, Any]:
    client_id = os.getenv("FYERS_CLIENT_ID")
    token = os.getenv("FYERS_ACCESS_TOKEN")
    if not client_id or not token:
        return {"executed": False, "status": "MISSING_ENV_CREDENTIALS", "rows": 0}
    try:
        from fyers_apiv3 import fyersModel  # type: ignore
    except Exception as exc:
        return {"executed": False, "status": "FYERS_SDK_NOT_INSTALLED", "error": str(exc), "rows": 0}
    try:
        fyers = fyersModel.FyersModel(client_id=client_id, token=token, is_async=False, log_path="")
        data = {
            "symbol": symbol,
            "resolution": "5",
            "date_format": "1",
            "range_from": trading_date,
            "range_to": trading_date,
            "cont_flag": "1",
        }
        response = fyers.history(data=data)
        candles = response.get("candles", []) if isinstance(response, dict) else []
        return {"executed": True, "status": "DATA_ONLY_HISTORY_CALL_COMPLETED", "rows": len(candles), "response_redacted": response}
    except Exception as exc:
        return {"executed": True, "status": "DATA_ONLY_HISTORY_CALL_FAILED", "error": str(exc), "rows": 0}


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = as_path(args.workspace)
    payload = base_payload(MODULE_NUMBER, MODULE_NAME, workspace, args.trading_date, args.day_number)
    sample = write_sample_candles(workspace, args.trading_date) if args.write else "not_written_without_write_flag"
    history_result = {"executed": False, "status": "OFFLINE_SAMPLE_SCHEMA_BY_DEFAULT", "rows": 0}
    if args.execute_live_data_only:
        history_result = _try_history(args.symbol, args.trading_date)
    failed = str(history_result.get("status", "")).endswith("FAILED")
    payload.update({
        "historical_5m_fetcher_status": "PASS" if not failed else "FAIL",
        "decision": "HISTORICAL_5M_DATA_ONLY_FETCHER_READY" if not args.execute_live_data_only else history_result.get("status"),
        "symbol": args.symbol,
        "sample_schema_file": sample,
        "execute_live_data_only_requested": bool(args.execute_live_data_only),
        "external_api_calls_executed": bool(history_result.get("executed")),
        "external_api_calls_executed_by_module_173": bool(history_result.get("executed")),
        "history_result": history_result,
        "secrets": credential_status(),
        "order_api_invoked_by_module_173": False,
        "broker_execution_invoked_by_module_173": False,
        "auto_trading_started_by_module_173": False,
        "fake_trades_created_by_module_173": False,
    })
    if args.write:
        payload["evidence_files"] = write_outputs(payload, workspace, BASENAME)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    add_common_cli(parser)
    parser.add_argument("--execute-live-data-only", action="store_true")
    args = parser.parse_args()
    if args.guard_check:
        print_payload(guard_payload(MODULE_NUMBER, MODULE_NAME))
        return 0
    payload = build_payload(args)
    print_payload(payload)
    return 0 if payload.get("historical_5m_fetcher_status") == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
