from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from hqe_live_paper_ops_172_180_common import add_common_cli, as_path, base_payload, guard_payload, print_payload, write_outputs

MODULE_NUMBER = 174
MODULE_NAME = "Live Data Symbol Config Guard"
BASENAME = "MODULE_174_LIVE_DATA_SYMBOL_CONFIG_GUARD_STATUS"

ALLOWED_SYMBOLS = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX", "NSE:FINNIFTY-INDEX"]


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = as_path(args.workspace)
    symbol_allowed = args.symbol in ALLOWED_SYMBOLS
    config_path = workspace / "HQE_LIVE_DATA_SYMBOL_CONFIG.json"
    payload = base_payload(MODULE_NUMBER, MODULE_NAME, workspace, args.trading_date, args.day_number)
    payload.update({
        "symbol_config_guard_status": "PASS" if symbol_allowed else "FAIL",
        "decision": "LIVE_DATA_SYMBOL_CONFIG_READY" if symbol_allowed else "LIVE_DATA_SYMBOL_NOT_ALLOWED",
        "requested_symbol": args.symbol,
        "allowed_symbols": ALLOWED_SYMBOLS,
        "data_interval": "5m",
        "market_session_start": "09:15",
        "market_session_end": "15:30",
        "option_buy_only": True,
        "option_selling_allowed": False,
        "external_api_calls_executed_by_module_174": False,
        "order_api_invoked_by_module_174": False,
        "broker_execution_invoked_by_module_174": False,
        "auto_trading_started_by_module_174": False,
        "fake_trades_created_by_module_174": False,
    })
    if args.write:
        config_path.write_text(json.dumps({
            "symbol": args.symbol,
            "data_interval": "5m",
            "session": {"start": "09:15", "end": "15:30"},
            "mode": "DATA_ONLY_PAPER_ONLY",
            "allowed_symbols": ALLOWED_SYMBOLS,
            "order_api_allowed": False,
            "broker_execution_allowed": False,
        }, indent=2), encoding="utf-8")
        payload["symbol_config_file"] = str(config_path)
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
    return 0 if payload.get("symbol_config_guard_status") == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
