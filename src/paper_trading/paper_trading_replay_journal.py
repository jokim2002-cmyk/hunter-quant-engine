"""
Paper Trading Replay Journal

Safe local bridge that runs fake/paper replay steps and persists a journal run.

No broker code. No real orders. Not live market data. Not a profitability claim.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.paper_trading.paper_trading_journal_store import (
    PaperTradingJournalRunPaths,
    write_paper_trading_journal_run,
)
from src.paper_trading.paper_trading_replay_loop import (
    PaperTradingReplayResult,
    PaperTradingReplayStep,
    run_paper_trading_replay_loop,
)
from src.paper_trading.paper_trading_session import PaperTradingSession


@dataclass(frozen=True)
class PaperTradingReplayJournalResult:
    """
    Result of a local fake/paper replay run with journal persistence.
    """

    replay_result: PaperTradingReplayResult
    journal_paths: PaperTradingJournalRunPaths

    @property
    def session(self) -> PaperTradingSession:
        """
        Return the paper session produced by the replay run.
        """
        return self.replay_result.session

    @property
    def processed_steps(self) -> int:
        """
        Return the number of processed replay steps.
        """
        return self.replay_result.processed_steps

    @property
    def submitted_orders_count(self) -> int:
        """
        Return the number of fake/paper submitted orders.
        """
        return self.replay_result.submitted_orders_count

    @property
    def exit_records_count(self) -> int:
        """
        Return the number of fake/paper exit records.
        """
        return self.replay_result.exit_records_count

    @property
    def has_missing_closes(self) -> bool:
        """
        Return True when a replay close step had no matching open position.
        """
        return self.replay_result.has_missing_closes


def run_paper_trading_replay_journal(
    steps: Iterable[PaperTradingReplayStep],
    output_dir: str | Path = Path("reports") / "paper_trading" / "journal",
    *,
    run_id: str | None = None,
    generated_at: datetime | None = None,
    session: PaperTradingSession | None = None,
) -> PaperTradingReplayJournalResult:
    """
    Run fake/paper replay steps and persist the resulting session journal.

    This is local-only. It never connects to a broker, never uses live market
    data, and never places real orders.
    """
    replay_result = run_paper_trading_replay_loop(steps, session=session)
    journal_paths = write_paper_trading_journal_run(
        replay_result.session,
        output_dir,
        run_id=run_id,
        generated_at=generated_at,
    )

    return PaperTradingReplayJournalResult(
        replay_result=replay_result,
        journal_paths=journal_paths,
    )
