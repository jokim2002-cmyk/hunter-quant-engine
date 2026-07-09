from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any, Dict, List

from hqe_live_paper_ops_172_180_common import add_common_cli, as_path, base_payload, create_cmd, guard_payload, print_payload, write_outputs

MODULE_NUMBER = 178
MODULE_NAME = "Live Paper Report Index V2"
BASENAME = "MODULE_178_LIVE_PAPER_REPORT_INDEX_V2_STATUS"

PATTERNS = ["*.md", "*.json", "*.csv", "*.html"]


def build_index(workspace: Path) -> Dict[str, Any]:
    files = []
    for pattern in PATTERNS:
        for path in sorted(workspace.glob(pattern)):
            if path.name.startswith("MODULE_") or path.name.startswith("HQE_") or path.name.startswith("DAY_") or path.name.startswith("FORWARD_") or path.name.startswith("FYERS_"):
                files.append(path)
    html_path = workspace / "HQE_LIVE_PAPER_REPORT_INDEX_V2.html"
    rows = []
    for path in files:
        rows.append(f"<tr><td>{html.escape(path.name)}</td><td><a href='{html.escape(path.as_uri())}'>Open</a></td></tr>")
    html_path.write_text(
        "<!doctype html><html><head><title>HQE Live Paper Report Index V2</title></head><body>"
        "<h1>HQE Live Paper Report Index V2</h1>"
        "<p>Paper-only evidence index. No orders. No broker execution.</p>"
        "<table border='1' cellspacing='0' cellpadding='6'><tr><th>File</th><th>Link</th></tr>"
        + "\n".join(rows)
        + "</table></body></html>",
        encoding="utf-8",
    )
    return {"html_index": str(html_path), "indexed_files_count": len(files)}


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = as_path(args.workspace)
    payload = base_payload(MODULE_NUMBER, MODULE_NAME, workspace, args.trading_date, args.day_number)
    result = build_index(workspace) if args.write else {"html_index": "not_written_without_write_flag", "indexed_files_count": 0}
    launcher = workspace / "OPEN_HQE_LIVE_PAPER_REPORT_INDEX_V2.cmd"
    payload.update({
        "report_index_v2_status": "PASS",
        "decision": "LIVE_PAPER_REPORT_INDEX_V2_READY_LOCAL_FILES_ONLY",
        **result,
        "launcher_path": str(launcher),
        "external_api_calls_executed_by_module_178": False,
        "order_api_invoked_by_module_178": False,
        "broker_execution_invoked_by_module_178": False,
        "auto_trading_started_by_module_178": False,
        "fake_trades_created_by_module_178": False,
    })
    if args.write:
        create_cmd(launcher, [f'start "" "{result["html_index"]}"'])
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
