"""
Paper Trading Replay Journal Demo CLI

Safe local demo for running fake/paper replay steps and writing a journal bundle.

No broker code. No real orders. Not live market data. Not a profitability claim.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_trading_journal_store import (
    clean_paper_trading_journal_run,
)
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_replay_journal import (
    run_paper_trading_replay_journal,
)
from src.paper_trading.paper_trading_replay_loop import PaperTradingReplayStep

REPORT_OUTPUT_DIR = Path("reports") / "paper_trading" / "journal"
DEMO_RUN_ID = "demo-replay-journal"

_OPENED_AT = datetime(2026, 7, 6, 9, 15, tzinfo=timezone.utc)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30, tzinfo=timezone.utc)


def run_demo() -> int:
    """
    Run a deterministic fake/paper replay journal demo.
    """
    print("Hunter Quant Engine - Paper Replay Journal Demo")
    print("fake/local paper replay only")
    print("no broker")
    print("no live market data")
    print("no real orders")
    print("not a profitability claim")

    request = PaperOrderRequest(
        symbol="NIFTY26JUL24200CE",
        quantity=65,
        planned_entry_price=100.0,
        created_at=_OPENED_AT,
        plan_id="demo-replay-journal-plan",
    )

    clean_paper_trading_journal_run(REPORT_OUTPUT_DIR, run_id=DEMO_RUN_ID)

    result = run_paper_trading_replay_journal(
        (
            PaperTradingReplayStep(
                timestamp=_OPENED_AT,
                request=request,
            ),
            PaperTradingReplayStep(
                timestamp=_CLOSED_AT,
                close_symbol="NIFTY26JUL24200CE",
                exit_reason=PaperExitReason.TARGET,
                exit_price=135.0,
                estimated_exit_charges=40.0,
                estimated_slippage=10.0,
            ),
        ),
        REPORT_OUTPUT_DIR,
        run_id=DEMO_RUN_ID,
        generated_at=_CLOSED_AT,
    )

    summary_path = result.journal_paths.summary_json
    manifest_path = result.journal_paths.manifest_json

    print("")
    print("Paper Replay Journal Summary")
    print(f"processed replay steps: {result.processed_steps}")
    print(f"paper submitted orders: {result.submitted_orders_count}")
    print(f"paper exit records: {result.exit_records_count}")
    print(f"paper missing closes: {result.replay_result.missing_close_symbols}")
    print(f"paper journal output dir: {result.journal_paths.output_dir}")
    print(f"paper journal summary json: {summary_path}")
    print(f"paper journal manifest json: {manifest_path}")
    print("paper replay journal files are local/generated")
    print("paper pnl is simulation only")
    print("estimated costs are included in net pnl only")
    print("gross pnl excludes costs")

    return 0


def main() -> int:
    """
    CLI entrypoint.
    """
    return run_demo()


if __name__ == "__main__":
    raise SystemExit(main())
