"""Guarded offline shadow sessions with append-only parity evidence.

This module remains disconnected from the canonical HQE paper runtime. It may
write only a dedicated parity-evidence journal outside the strategy namespace.
It never writes strategy state, the trading ledger, Module 131 files, or broker
execution artifacts.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.errors import (
    ParityJournalError,
    ShadowSessionError,
)
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.recovery import (
    OfflineRecoveryReadiness,
    OfflineRestartRecoverySnapshot,
)
from src.multi_strategy.shadow import (
    OfflineShadowParityRunner,
    ShadowParityResult,
    ShadowParityStatus,
)

PARITY_JOURNAL_SCHEMA_VERSION = "1.0.0"
SHADOW_SESSION_SCHEMA_VERSION = "1.0.0"
_SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_.+-]{1,128}$")


class ParityEvidenceEventType(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    PARITY_MATCH = "PARITY_MATCH"
    PARITY_MISMATCH = "PARITY_MISMATCH"
    SESSION_CLOSED = "SESSION_CLOSED"


class ShadowSessionStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    HALTED = "HALTED"
    CLOSED = "CLOSED"


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(
            root.resolve(strict=False)
        )
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class ParityEvidenceRecord:
    """One immutable chained parity-evidence journal record."""

    event_type: ParityEvidenceEventType
    session_id: str
    sequence: int
    event_time: str
    selection_hash: str
    recovery_snapshot_hash: str
    previous_record_hash: str
    cycle_id: str = ""
    input_identity: str = ""
    result_hash: str = ""
    parity_status: str = ""
    mismatch_reasons: tuple[str, ...] = ()
    details: Mapping[str, Any] = MappingProxyType({})
    schema_version: str = PARITY_JOURNAL_SCHEMA_VERSION
    runtime_connected: bool = False
    runtime_cutover_performed: bool = False
    state_written: bool = False
    ledger_written: bool = False

    def __post_init__(self) -> None:
        issues: list[str] = []
        if self.schema_version != PARITY_JOURNAL_SCHEMA_VERSION:
            issues.append("unsupported parity journal schema version")
        if not _SAFE_SESSION_ID.fullmatch(str(self.session_id)):
            issues.append("invalid session_id")
        if not isinstance(self.sequence, int) or self.sequence < 1:
            issues.append("sequence must be a positive integer")
        if not str(self.event_time).strip():
            issues.append("event_time is required")
        if not str(self.selection_hash).strip():
            issues.append("selection_hash is required")
        if not str(self.recovery_snapshot_hash).strip():
            issues.append("recovery_snapshot_hash is required")
        if self.sequence == 1 and self.previous_record_hash:
            issues.append("first record cannot have previous_record_hash")
        if self.sequence > 1 and not self.previous_record_hash:
            issues.append("chained record requires previous_record_hash")
        if (
            self.runtime_connected
            or self.runtime_cutover_performed
            or self.state_written
            or self.ledger_written
        ):
            issues.append(
                "parity evidence cannot connect/cut over runtime or write "
                "state/ledger"
            )

        if self.event_type in {
            ParityEvidenceEventType.PARITY_MATCH,
            ParityEvidenceEventType.PARITY_MISMATCH,
        }:
            if not self.cycle_id:
                issues.append("parity record requires cycle_id")
            if not self.input_identity:
                issues.append("parity record requires input_identity")
            if not self.result_hash:
                issues.append("parity record requires result_hash")
            expected = (
                ShadowParityStatus.MATCH.value
                if self.event_type
                is ParityEvidenceEventType.PARITY_MATCH
                else ShadowParityStatus.MISMATCH.value
            )
            if self.parity_status != expected:
                issues.append(
                    "parity_status does not match parity event type"
                )
            if (
                self.event_type is ParityEvidenceEventType.PARITY_MATCH
                and self.mismatch_reasons
            ):
                issues.append("PARITY_MATCH cannot contain mismatch reasons")
            if (
                self.event_type is ParityEvidenceEventType.PARITY_MISMATCH
                and not self.mismatch_reasons
            ):
                issues.append(
                    "PARITY_MISMATCH requires mismatch reasons"
                )
        else:
            if (
                self.cycle_id
                or self.input_identity
                or self.result_hash
                or self.parity_status
                or self.mismatch_reasons
            ):
                issues.append(
                    "session boundary record cannot contain parity fields"
                )

        if issues:
            raise ParityJournalError("; ".join(issues))
        object.__setattr__(self, "details", _freeze(self.details))
        object.__setattr__(
            self,
            "mismatch_reasons",
            tuple(str(item) for item in self.mismatch_reasons),
        )

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "event_time": self.event_time,
            "selection_hash": self.selection_hash,
            "recovery_snapshot_hash": self.recovery_snapshot_hash,
            "previous_record_hash": self.previous_record_hash,
            "cycle_id": self.cycle_id,
            "input_identity": self.input_identity,
            "result_hash": self.result_hash,
            "parity_status": self.parity_status,
            "mismatch_reasons": list(self.mismatch_reasons),
            "details": dict(self.details),
            "runtime_connected": self.runtime_connected,
            "runtime_cutover_performed": (
                self.runtime_cutover_performed
            ),
            "state_written": self.state_written,
            "ledger_written": self.ledger_written,
        }

    @property
    def record_hash(self) -> str:
        return canonical_mapping_hash(self._hash_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._hash_payload(),
            "record_hash": self.record_hash,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "ParityEvidenceRecord":
        raw_details = payload.get("details", {})
        if not isinstance(raw_details, Mapping):
            raise ParityJournalError("record details must be a mapping")
        raw_reasons = payload.get("mismatch_reasons", ())
        if not isinstance(raw_reasons, (list, tuple)):
            raise ParityJournalError(
                "mismatch_reasons must be a list"
            )
        try:
            event_type = ParityEvidenceEventType(
                str(payload.get("event_type", ""))
            )
        except ValueError as exc:
            raise ParityJournalError("invalid event_type") from exc

        record = cls(
            schema_version=str(payload.get("schema_version", "")),
            event_type=event_type,
            session_id=str(payload.get("session_id", "")),
            sequence=int(payload.get("sequence", 0)),
            event_time=str(payload.get("event_time", "")),
            selection_hash=str(payload.get("selection_hash", "")),
            recovery_snapshot_hash=str(
                payload.get("recovery_snapshot_hash", "")
            ),
            previous_record_hash=str(
                payload.get("previous_record_hash", "")
            ),
            cycle_id=str(payload.get("cycle_id", "")),
            input_identity=str(payload.get("input_identity", "")),
            result_hash=str(payload.get("result_hash", "")),
            parity_status=str(payload.get("parity_status", "")),
            mismatch_reasons=tuple(str(item) for item in raw_reasons),
            details=dict(raw_details),
            runtime_connected=bool(
                payload.get("runtime_connected", False)
            ),
            runtime_cutover_performed=bool(
                payload.get("runtime_cutover_performed", False)
            ),
            state_written=bool(payload.get("state_written", False)),
            ledger_written=bool(payload.get("ledger_written", False)),
        )
        supplied_hash = str(payload.get("record_hash", ""))
        if not supplied_hash:
            raise ParityJournalError("record_hash is required")
        if supplied_hash != record.record_hash:
            raise ParityJournalError(
                "record_hash does not match record contents"
            )
        return record


class ParityEvidenceJournal:
    """Single-writer append-only JSONL journal with a SHA-256 chain."""

    def __init__(
        self,
        path: str | Path,
        *,
        runtime_connected: bool = False,
    ) -> None:
        if runtime_connected:
            raise ParityJournalError(
                "parity journal cannot connect to canonical runtime"
            )
        self.path = Path(path).resolve(strict=False)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.runtime_connected = False

    def _acquire_lock(self) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return os.open(
                self.lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as exc:
            raise ParityJournalError(
                "parity journal is locked by another writer"
            ) from exc

    def _release_lock(self, descriptor: int) -> None:
        try:
            os.close(descriptor)
        finally:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def read_records(self) -> tuple[ParityEvidenceRecord, ...]:
        if not self.path.exists():
            return ()
        if not self.path.is_file():
            raise ParityJournalError(
                "parity journal path is not a regular file"
            )
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ParityJournalError(
                "unable to read parity journal"
            ) from exc

        records: list[ParityEvidenceRecord] = []
        previous_hash = ""
        session_id = ""
        seen_cycles: set[str] = set()
        closed = False

        for index, line in enumerate(lines, start=1):
            if not line.strip():
                raise ParityJournalError(
                    f"blank parity journal line at sequence {index}"
                )
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ParityJournalError(
                    f"invalid JSON at parity journal line {index}"
                ) from exc
            if not isinstance(payload, Mapping):
                raise ParityJournalError(
                    f"journal line {index} must contain an object"
                )
            record = ParityEvidenceRecord.from_dict(payload)
            if record.sequence != index:
                raise ParityJournalError(
                    "parity journal sequence is not contiguous"
                )
            if record.previous_record_hash != previous_hash:
                raise ParityJournalError(
                    "parity journal hash chain is broken"
                )
            if index == 1:
                if (
                    record.event_type
                    is not ParityEvidenceEventType.SESSION_STARTED
                ):
                    raise ParityJournalError(
                        "first journal record must start the session"
                    )
                session_id = record.session_id
            elif record.session_id != session_id:
                raise ParityJournalError(
                    "journal contains multiple session IDs"
                )
            if closed:
                raise ParityJournalError(
                    "journal contains records after SESSION_CLOSED"
                )
            if record.cycle_id:
                if record.cycle_id in seen_cycles:
                    raise ParityJournalError(
                        f"duplicate cycle_id '{record.cycle_id}'"
                    )
                seen_cycles.add(record.cycle_id)
            if (
                record.event_type
                is ParityEvidenceEventType.SESSION_CLOSED
            ):
                closed = True
            records.append(record)
            previous_hash = record.record_hash

        return tuple(records)

    def append(
        self,
        *,
        event_type: ParityEvidenceEventType,
        session_id: str,
        event_time: str,
        selection_hash: str,
        recovery_snapshot_hash: str,
        cycle_id: str = "",
        input_identity: str = "",
        result_hash: str = "",
        parity_status: str = "",
        mismatch_reasons: Iterable[str] = (),
        details: Mapping[str, Any] | None = None,
    ) -> ParityEvidenceRecord:
        descriptor = self._acquire_lock()
        try:
            records = self.read_records()
            if records and (
                records[-1].event_type
                is ParityEvidenceEventType.SESSION_CLOSED
            ):
                raise ParityJournalError(
                    "cannot append after SESSION_CLOSED"
                )
            if records:
                if records[0].session_id != session_id:
                    raise ParityJournalError(
                        "session_id does not match existing journal"
                    )
                if (
                    event_type
                    is ParityEvidenceEventType.SESSION_STARTED
                ):
                    raise ParityJournalError(
                        "session has already been started"
                    )
            elif (
                event_type
                is not ParityEvidenceEventType.SESSION_STARTED
            ):
                raise ParityJournalError(
                    "first journal event must be SESSION_STARTED"
                )

            if cycle_id and any(
                item.cycle_id == cycle_id for item in records
            ):
                raise ParityJournalError(
                    f"duplicate cycle_id '{cycle_id}'"
                )

            record = ParityEvidenceRecord(
                event_type=event_type,
                session_id=session_id,
                sequence=len(records) + 1,
                event_time=str(event_time),
                selection_hash=str(selection_hash),
                recovery_snapshot_hash=str(
                    recovery_snapshot_hash
                ),
                previous_record_hash=(
                    records[-1].record_hash if records else ""
                ),
                cycle_id=str(cycle_id),
                input_identity=str(input_identity),
                result_hash=str(result_hash),
                parity_status=str(parity_status),
                mismatch_reasons=tuple(
                    str(item) for item in mismatch_reasons
                ),
                details=dict(details or {}),
            )
            line = json.dumps(
                record.to_dict(),
                sort_keys=True,
                separators=(",", ":"),
            ) + "\n"
            try:
                with self.path.open(
                    "a",
                    encoding="utf-8",
                    newline="\n",
                ) as handle:
                    handle.write(line)
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                raise ParityJournalError(
                    "unable to append parity journal"
                ) from exc
            return record
        finally:
            self._release_lock(descriptor)


@dataclass(frozen=True)
class ShadowSessionSummary:
    schema_version: str
    session_id: str
    status: ShadowSessionStatus
    selection_hash: str
    recovery_snapshot_hash: str
    journal_path: str
    record_count: int
    cycle_count: int
    match_count: int
    mismatch_count: int
    first_record_hash: str
    last_record_hash: str
    runtime_connected: bool = False
    runtime_cutover_performed: bool = False
    state_written: bool = False
    ledger_written: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != SHADOW_SESSION_SCHEMA_VERSION:
            raise ShadowSessionError(
                "unsupported shadow session schema version"
            )
        if (
            self.runtime_connected
            or self.runtime_cutover_performed
            or self.state_written
            or self.ledger_written
        ):
            raise ShadowSessionError(
                "shadow session summary contains forbidden lifecycle flags"
            )

    @property
    def summary_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "status": self.status.value,
            "selection_hash": self.selection_hash,
            "recovery_snapshot_hash": self.recovery_snapshot_hash,
            "journal_path": self.journal_path,
            "record_count": self.record_count,
            "cycle_count": self.cycle_count,
            "match_count": self.match_count,
            "mismatch_count": self.mismatch_count,
            "first_record_hash": self.first_record_hash,
            "last_record_hash": self.last_record_hash,
            "runtime_connected": self.runtime_connected,
            "runtime_cutover_performed": (
                self.runtime_cutover_performed
            ),
            "state_written": self.state_written,
            "ledger_written": self.ledger_written,
        }
        if include_hash:
            payload["summary_hash"] = self.summary_hash
        return payload


class GuardedShadowSessionController:
    """Run repeated shadow cycles and journal evidence outside lifecycle state."""

    def __init__(
        self,
        *,
        runner: OfflineShadowParityRunner,
        recovery: OfflineRestartRecoverySnapshot,
        journal: ParityEvidenceJournal,
        session_id: str,
        runtime_connected: bool = False,
    ) -> None:
        if runtime_connected:
            raise ShadowSessionError(
                "shadow session cannot connect to canonical runtime"
            )
        if not _SAFE_SESSION_ID.fullmatch(str(session_id)):
            raise ShadowSessionError("invalid shadow session_id")
        if recovery.readiness is not OfflineRecoveryReadiness.READY_FLAT:
            raise ShadowSessionError(
                "shadow session requires READY_FLAT recovery"
            )
        if recovery.runtime_connected or recovery.runtime_cutover_performed:
            raise ShadowSessionError(
                "shadow session requires offline recovery evidence"
            )
        namespace = Path(recovery.namespace_directory)
        if _is_within(namespace, journal.path):
            raise ShadowSessionError(
                "parity journal must be outside strategy namespace"
            )
        if journal.read_records():
            raise ShadowSessionError(
                "shadow session requires a new empty journal"
            )

        self._runner = runner
        self._recovery = recovery
        self._journal = journal
        self._session_id = str(session_id)
        self._status = ShadowSessionStatus.CREATED
        self.runtime_connected = False

    @property
    def status(self) -> ShadowSessionStatus:
        return self._status

    def start(self, *, event_time: str) -> ParityEvidenceRecord:
        if self._status is not ShadowSessionStatus.CREATED:
            raise ShadowSessionError(
                "shadow session can only be started once"
            )
        record = self._journal.append(
            event_type=ParityEvidenceEventType.SESSION_STARTED,
            session_id=self._session_id,
            event_time=event_time,
            selection_hash=(
                self._recovery.selection.selection_hash
            ),
            recovery_snapshot_hash=self._recovery.snapshot_hash,
            details={
                "mode": "OFFLINE_SHADOW_SESSION",
                "activation_status": (
                    self._recovery.selection.activation_status.value
                ),
                "runtime_connected": False,
                "runtime_cutover_performed": False,
                "state_written": False,
                "ledger_written": False,
            },
        )
        self._status = ShadowSessionStatus.RUNNING
        return record

    def run_cycle(
        self,
        *,
        cycle_id: str,
        event_time: str,
        request: Any,
        evidence_details: Mapping[str, Any] | None = None,
    ) -> ShadowParityResult:
        if self._status is not ShadowSessionStatus.RUNNING:
            raise ShadowSessionError(
                "shadow cycle requires a RUNNING session"
            )
        if not str(cycle_id).strip():
            raise ShadowSessionError("cycle_id is required")

        result = self._runner.run(request)
        if (
            result.selection_hash
            != self._recovery.selection.selection_hash
        ):
            raise ShadowSessionError(
                "shadow result selection identity mismatch"
            )
        if result.recovery_snapshot_hash != self._recovery.snapshot_hash:
            raise ShadowSessionError(
                "shadow result recovery identity mismatch"
            )
        event_type = (
            ParityEvidenceEventType.PARITY_MATCH
            if result.status is ShadowParityStatus.MATCH
            else ParityEvidenceEventType.PARITY_MISMATCH
        )
        extra_details = dict(evidence_details or {})
        protected_detail_keys = {
            "signal",
            "option_side",
            "execution_mode",
            "runtime_connected",
            "runtime_cutover_performed",
            "state_written",
            "ledger_written",
        }
        overlap = protected_detail_keys.intersection(extra_details)
        if overlap:
            raise ShadowSessionError(
                "evidence details cannot override protected keys: "
                + ", ".join(sorted(overlap))
            )
        details = {
            "signal": result.registered_result.decision.signal,
            "option_side": (
                result.registered_result.decision.option_side
            ),
            "execution_mode": result.execution_mode.value,
            "runtime_connected": False,
            "runtime_cutover_performed": False,
            "state_written": False,
            "ledger_written": False,
            **extra_details,
        }
        self._journal.append(
            event_type=event_type,
            session_id=self._session_id,
            event_time=event_time,
            selection_hash=result.selection_hash,
            recovery_snapshot_hash=result.recovery_snapshot_hash,
            cycle_id=str(cycle_id),
            input_identity=result.input_identity,
            result_hash=result.result_hash,
            parity_status=result.status.value,
            mismatch_reasons=result.mismatch_reasons,
            details=details,
        )
        if result.status is ShadowParityStatus.MISMATCH:
            self._status = ShadowSessionStatus.HALTED
            raise ShadowSessionError(
                "shadow session halted on parity mismatch: "
                + "; ".join(result.mismatch_reasons)
            )
        return result


    def journal_records(self) -> tuple[ParityEvidenceRecord, ...]:
        """Return the validated parity journal records read-only."""

        return self._journal.read_records()

    def close(self, *, event_time: str) -> ParityEvidenceRecord:
        if self._status not in {
            ShadowSessionStatus.RUNNING,
            ShadowSessionStatus.HALTED,
        }:
            raise ShadowSessionError(
                "only a running or halted session can be closed"
            )
        prior_status = self._status
        record = self._journal.append(
            event_type=ParityEvidenceEventType.SESSION_CLOSED,
            session_id=self._session_id,
            event_time=event_time,
            selection_hash=(
                self._recovery.selection.selection_hash
            ),
            recovery_snapshot_hash=self._recovery.snapshot_hash,
            details={
                "prior_status": prior_status.value,
                "runtime_connected": False,
                "runtime_cutover_performed": False,
                "state_written": False,
                "ledger_written": False,
            },
        )
        self._status = ShadowSessionStatus.CLOSED
        return record

    def summary(self) -> ShadowSessionSummary:
        records = self._journal.read_records()
        parity_records = tuple(
            item
            for item in records
            if item.event_type
            in {
                ParityEvidenceEventType.PARITY_MATCH,
                ParityEvidenceEventType.PARITY_MISMATCH,
            }
        )
        return ShadowSessionSummary(
            schema_version=SHADOW_SESSION_SCHEMA_VERSION,
            session_id=self._session_id,
            status=self._status,
            selection_hash=(
                self._recovery.selection.selection_hash
            ),
            recovery_snapshot_hash=self._recovery.snapshot_hash,
            journal_path=str(self._journal.path),
            record_count=len(records),
            cycle_count=len(parity_records),
            match_count=sum(
                item.event_type
                is ParityEvidenceEventType.PARITY_MATCH
                for item in parity_records
            ),
            mismatch_count=sum(
                item.event_type
                is ParityEvidenceEventType.PARITY_MISMATCH
                for item in parity_records
            ),
            first_record_hash=(
                records[0].record_hash if records else ""
            ),
            last_record_hash=(
                records[-1].record_hash if records else ""
            ),
        )
