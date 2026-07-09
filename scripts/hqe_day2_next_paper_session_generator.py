from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict

from hqe_live_paper_ops_172_180_common import add_common_cli, as_path, base_payload, guard_payload, print_payload, write_outputs

MODULE_NUMBER = 175
MODULE_NAME = "Next Paper Session Day Generator"
BASENAME = "MODULE_175_NEXT_PAPER_SESSION_DAY_GENERATOR_STATUS"


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = as_path(args.workspace)
    next_day = max(int(args.day_number) + 1, 2)
    day_tag = f"DAY_{next_day:03d}"
    files = {
        "trade_log": workspace / f"{day_tag}_FORWARD_TRADE_LOG.csv",
        "paper_execution_log": workspace / f"{day_tag}_PAPER_EXECUTION_LOG.csv",
        "no_trade_reason": workspace / f"{day_tag}_PAPER_SIGNAL_NO_TRADE_REASON.md",
        "operator_notes": workspace / f"{day_tag}_OPERATOR_NOTES.md",
    }
    payload = base_payload(MODULE_NUMBER, MODULE_NAME, workspace, args.trading_date, next_day)
    payload.update({
        "next_session_generator_status": "PASS",
        "decision": "NEXT_PAPER_SESSION_FILES_READY_NO_FAKE_TRADES",
        "generated_day_number": next_day,
        "generated_day_tag": day_tag,
        "created_or_verified_files": {k: str(v) for k, v in files.items()},
        "fake_trade_rows_created": False,
        "external_api_calls_executed_by_module_175": False,
        "order_api_invoked_by_module_175": False,
        "broker_execution_invoked_by_module_175": False,
        "auto_trading_started_by_module_175": False,
        "fake_trades_created_by_module_175": False,
    })
    if args.write:
        workspace.mkdir(parents=True, exist_ok=True)
        for key, path in files.items():
            if path.suffix.lower() == ".csv" and not path.exists():
                with path.open("w", encoding="utf-8", newline="") as fh:
                    writer = csv.writer(fh)
                    writer.writerow(["trading_date", "day_number", "timestamp", "symbol", "action", "status", "notes"])
            elif path.suffix.lower() == ".md" and not path.exists():
                path.write_text(f"# {day_tag} Paper Session\n\nNo fake trades. Paper-only. Manual operator review required.\n", encoding="utf-8")
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
