from __future__ import annotations

import hashlib

import pytest

from src.multi_strategy.errors import OperatorEvidenceViewError, ParityJournalError
from src.multi_strategy.evidence_view import OperatorEvidenceViewReader
from src.multi_strategy.session import (
    ParityEvidenceEventType,
    ParityEvidenceJournal,
)


def build_journal(path):
    journal = ParityEvidenceJournal(path)
    journal.append(
        event_type=ParityEvidenceEventType.SESSION_STARTED,
        session_id="operator-session",
        event_time="2026-07-16T11:00:00+05:30",
        selection_hash="selection-hash",
        recovery_snapshot_hash="recovery-hash",
        details={"mode": "OFFLINE_SHADOW_SESSION"},
    )
    for index, (signal, side) in enumerate(
        (("LONG", "CE_BUY"), ("SHORT", "PE_BUY"), ("NEUTRAL", "NO_TRADE")),
        start=1,
    ):
        journal.append(
            event_type=ParityEvidenceEventType.PARITY_MATCH,
            session_id="operator-session",
            event_time=f"2026-07-16T11:{index * 5:02d}:00+05:30",
            selection_hash="selection-hash",
            recovery_snapshot_hash="recovery-hash",
            cycle_id=f"cycle-{index:03d}",
            input_identity=f"input-{index}",
            result_hash=f"result-{index}",
            parity_status="MATCH",
            details={
                "signal": signal,
                "option_side": side,
                "runtime_status_observed": "RUNNING",
                "runtime_observation_hash": f"observation-{index}",
            },
        )
    journal.append(
        event_type=ParityEvidenceEventType.SESSION_CLOSED,
        session_id="operator-session",
        event_time="2026-07-16T11:20:00+05:30",
        selection_hash="selection-hash",
        recovery_snapshot_hash="recovery-hash",
        details={"prior_status": "RUNNING"},
    )
    return journal


def test_operator_view_validates_chain_and_summarizes_cycles(tmp_path):
    journal = build_journal(tmp_path / "parity.jsonl")
    before = hashlib.sha256(journal.path.read_bytes()).hexdigest()

    view = OperatorEvidenceViewReader(journal.path).read()

    assert view.overall_status == "PASS_CLOSED"
    assert view.cycle_count == 3
    assert view.match_count == 3
    assert view.mismatch_count == 0
    assert view.signal_counts == {"LONG": 1, "SHORT": 1, "NEUTRAL": 1}
    assert view.option_side_counts["CE_BUY"] == 1
    assert view.runtime_status_counts == {"RUNNING": 3}
    assert len(view.observation_hashes) == 3
    assert "Canonical runtime connected: **NO**" in view.render_markdown()
    assert hashlib.sha256(journal.path.read_bytes()).hexdigest() == before


def test_operator_view_rejects_journal_inside_strategy_namespace(tmp_path):
    namespace = tmp_path / "strategies" / "id" / "1.0.0" / "hash"
    journal = build_journal(namespace / "parity.jsonl")

    with pytest.raises(OperatorEvidenceViewError, match="outside"):
        OperatorEvidenceViewReader(
            journal.path,
            strategy_namespace=namespace,
        )


def test_operator_view_rejects_tampered_journal(tmp_path):
    journal = build_journal(tmp_path / "parity.jsonl")
    text = journal.path.read_text(encoding="utf-8")
    journal.path.write_text(text.replace("CE_BUY", "PE_BUY", 1), encoding="utf-8")

    with pytest.raises(ParityJournalError):
        OperatorEvidenceViewReader(journal.path).read()


def test_operator_view_requires_existing_journal(tmp_path):
    with pytest.raises(OperatorEvidenceViewError, match="does not exist"):
        OperatorEvidenceViewReader(tmp_path / "missing.jsonl").read()
