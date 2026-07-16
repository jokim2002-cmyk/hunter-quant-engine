from __future__ import annotations

import json
import os

import pytest

from src.multi_strategy.errors import ParityJournalError
from src.multi_strategy.session import (
    ParityEvidenceEventType,
    ParityEvidenceJournal,
)


def append_start(journal: ParityEvidenceJournal):
    return journal.append(
        event_type=ParityEvidenceEventType.SESSION_STARTED,
        session_id="session-001",
        event_time="2026-07-16T10:00:00+05:30",
        selection_hash="selection-hash",
        recovery_snapshot_hash="recovery-hash",
        details={"mode": "test"},
    )


def append_match(journal: ParityEvidenceJournal, cycle_id="cycle-001"):
    return journal.append(
        event_type=ParityEvidenceEventType.PARITY_MATCH,
        session_id="session-001",
        event_time="2026-07-16T10:05:00+05:30",
        selection_hash="selection-hash",
        recovery_snapshot_hash="recovery-hash",
        cycle_id=cycle_id,
        input_identity="sha256:input",
        result_hash="result-hash",
        parity_status="MATCH",
        details={"signal": "LONG"},
    )


def test_append_only_journal_builds_contiguous_hash_chain(tmp_path):
    journal = ParityEvidenceJournal(tmp_path / "parity.jsonl")
    first = append_start(journal)
    second = append_match(journal)
    third = journal.append(
        event_type=ParityEvidenceEventType.SESSION_CLOSED,
        session_id="session-001",
        event_time="2026-07-16T10:10:00+05:30",
        selection_hash="selection-hash",
        recovery_snapshot_hash="recovery-hash",
        details={"prior_status": "RUNNING"},
    )

    records = journal.read_records()
    assert records == (first, second, third)
    assert records[0].sequence == 1
    assert records[1].previous_record_hash == records[0].record_hash
    assert records[2].previous_record_hash == records[1].record_hash


def test_journal_rejects_tampered_record_hash(tmp_path):
    journal = ParityEvidenceJournal(tmp_path / "parity.jsonl")
    append_start(journal)
    append_match(journal)

    lines = journal.path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[1])
    payload["result_hash"] = "tampered"
    lines[1] = json.dumps(payload, sort_keys=True)
    journal.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ParityJournalError, match="record_hash"):
        journal.read_records()


def test_journal_rejects_duplicate_cycle_and_append_after_close(tmp_path):
    journal = ParityEvidenceJournal(tmp_path / "parity.jsonl")
    append_start(journal)
    append_match(journal)

    with pytest.raises(ParityJournalError, match="duplicate cycle_id"):
        append_match(journal)

    journal.append(
        event_type=ParityEvidenceEventType.SESSION_CLOSED,
        session_id="session-001",
        event_time="2026-07-16T10:10:00+05:30",
        selection_hash="selection-hash",
        recovery_snapshot_hash="recovery-hash",
    )
    with pytest.raises(ParityJournalError, match="SESSION_CLOSED"):
        append_match(journal, cycle_id="cycle-002")


def test_journal_rejects_non_start_first_record(tmp_path):
    journal = ParityEvidenceJournal(tmp_path / "parity.jsonl")
    with pytest.raises(ParityJournalError, match="first journal event"):
        append_match(journal)


def test_journal_refuses_runtime_connection_and_active_lock(tmp_path):
    with pytest.raises(ParityJournalError, match="cannot connect"):
        ParityEvidenceJournal(
            tmp_path / "parity.jsonl",
            runtime_connected=True,
        )

    journal = ParityEvidenceJournal(tmp_path / "parity.jsonl")
    journal.lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        journal.lock_path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
    )
    os.close(descriptor)
    try:
        with pytest.raises(ParityJournalError, match="locked"):
            append_start(journal)
    finally:
        journal.lock_path.unlink()


def test_mismatch_record_requires_reasons(tmp_path):
    journal = ParityEvidenceJournal(tmp_path / "parity.jsonl")
    append_start(journal)

    with pytest.raises(
        ParityJournalError,
        match="requires mismatch reasons",
    ):
        journal.append(
            event_type=ParityEvidenceEventType.PARITY_MISMATCH,
            session_id="session-001",
            event_time="2026-07-16T10:05:00+05:30",
            selection_hash="selection-hash",
            recovery_snapshot_hash="recovery-hash",
            cycle_id="cycle-001",
            input_identity="sha256:input",
            result_hash="result-hash",
            parity_status="MISMATCH",
        )
