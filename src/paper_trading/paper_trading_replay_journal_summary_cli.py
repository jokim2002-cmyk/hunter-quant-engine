"""
Paper Trading Replay Journal Summary CLI

Prints a trader-friendly local fake/paper replay journal summary.

No broker code. No real orders. Not live market data. Not a profitability claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_REPLAY_JOURNAL_SUMMARY_JSON = (
    Path("reports")
    / "paper_trading"
    / "journal"
    / "demo-replay-journal"
    / "summary.json"
)


def load_replay_journal_summary(
    summary_json: str | Path = DEFAULT_REPLAY_JOURNAL_SUMMARY_JSON,
) -> dict[str, Any]:
    """
    Load a local fake/paper replay journal summary JSON payload.
    """
    path = Path(summary_json)
    if not path.exists():
        raise FileNotFoundError(
            f"paper replay journal summary not found: {path}. "
            "Run hqe_paper_replay_journal.bat first."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("paper replay journal summary must be a JSON object")

    return payload


def format_replay_journal_summary(payload: dict[str, Any]) -> str:
    """
    Format a local fake/paper replay journal summary for terminal output.
    """
    lines = [
        "Hunter Quant Engine - Paper Replay Journal Summary",
        "fake/local paper replay only",
        "no broker",
        "no live market data",
        "no real orders",
        "not a profitability claim",
        "paper pnl is simulation only",
        "",
        "Session",
        f"session id: {_first_value(payload, ('session_id', 'run_id'))}",
        f"started at: {_first_value(payload, ('started_at', 'generated_at'))}",
        "",
        "Orders",
        f"total orders: {_first_value(payload, ('total_orders',), 0)}",
        f"accepted orders: {_first_value(payload, ('accepted_orders',), 0)}",
        f"rejected orders: {_first_value(payload, ('rejected_orders',), 0)}",
        "",
        "Positions",
        f"open positions: {_first_value(payload, ('open_positions',), 0)}",
        f"closed trades: {_first_value(payload, ('closed_trades', 'closed_positions'), 0)}",
        f"exit records: {_first_value(payload, ('exit_records', 'total_exit_records'), 0)}",
        "",
        "Simulated PnL",
        f"gross pnl: {_first_value(payload, ('total_simulated_gross_pnl', 'simulated_gross_pnl'), 'unknown')}",
        f"estimated costs: {_first_value(payload, ('total_estimated_costs', 'estimated_costs'), 'unknown')}",
        f"net pnl: {_first_value(payload, ('total_simulated_net_pnl', 'simulated_net_pnl'), 'unknown')}",
        "",
        "Result Counts",
        f"wins: {_first_value(payload, ('net_winning_trades', 'winning_trades'), 'unknown')}",
        f"losses: {_first_value(payload, ('net_losing_trades', 'losing_trades'), 'unknown')}",
        f"flat: {_first_value(payload, ('net_flat_trades', 'flat_trades'), 'unknown')}",
        f"unknown: {_first_value(payload, ('net_unknown_trades', 'unknown_trades'), 'unknown')}",
    ]

    return "\n".join(lines)


def run_summary_view(
    summary_json: str | Path = DEFAULT_REPLAY_JOURNAL_SUMMARY_JSON,
) -> int:
    """
    Print the local fake/paper replay journal summary.
    """
    try:
        payload = load_replay_journal_summary(summary_json)
    except FileNotFoundError as error:
        print(f"ERROR: {error}")
        return 1

    print(format_replay_journal_summary(payload))
    return 0


def main() -> int:
    """
    CLI entrypoint.
    """
    return run_summary_view()


def _first_value(
    payload: dict[str, Any],
    keys: tuple[str, ...],
    default: Any = "unknown",
) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return default


if __name__ == "__main__":
    raise SystemExit(main())
