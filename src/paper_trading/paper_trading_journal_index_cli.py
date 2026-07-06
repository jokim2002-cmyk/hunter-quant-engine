"""
Paper Trading Journal Index CLI

Prints a trader-friendly local fake/paper replay journal run list.

No broker code. No real orders. Not live market data. Not a profitability claim.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.paper_trading.paper_trading_journal_store import (
    read_paper_trading_journal_index,
)

DEFAULT_JOURNAL_OUTPUT_DIR = Path("reports") / "paper_trading" / "journal"


def format_paper_trading_journal_index(payload: dict[str, Any]) -> str:
    """
    Format a local fake/paper replay journal index for terminal output.
    """
    runs = payload.get("runs", [])

    lines = [
        "Hunter Quant Engine - Paper Replay Journal Runs",
        "fake/local paper replay only",
        "no broker",
        "no live market data",
        "no real orders",
        "not a profitability claim",
        "paper pnl is simulation only",
        "",
        f"journal source: {payload.get('journal_source', 'paper')}",
        f"runs count: {len(runs)}",
    ]

    if not runs:
        lines.extend(
            [
                "",
                "No replay journal runs found.",
                "Run hqe_paper_replay_journal.bat first.",
            ]
        )
        return "\n".join(lines)

    lines.append("")

    for index, run in enumerate(runs, start=1):
        lines.extend(
            [
                f"{index}. run id: {run.get('run_id', '')}",
                f"   generated at: {run.get('generated_at', '')}",
                f"   output dir: {run.get('output_dir', '')}",
                f"   summary json: {run.get('summary_json', '')}",
                f"   manifest json: {run.get('manifest_json', '')}",
            ]
        )

    return "\n".join(lines)


def run_index_view(
    output_dir: str | Path = DEFAULT_JOURNAL_OUTPUT_DIR,
) -> int:
    """
    Print the local fake/paper replay journal run list.
    """
    payload = read_paper_trading_journal_index(output_dir)
    print(format_paper_trading_journal_index(payload))
    return 0


def main() -> int:
    """
    CLI entrypoint.
    """
    return run_index_view()


if __name__ == "__main__":
    raise SystemExit(main())
