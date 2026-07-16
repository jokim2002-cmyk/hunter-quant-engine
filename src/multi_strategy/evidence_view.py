"""Read-only operator evidence view for HQE parity journals."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.errors import OperatorEvidenceViewError
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.session import (
    ParityEvidenceEventType,
    ParityEvidenceJournal,
    ShadowSessionStatus,
)

OPERATOR_EVIDENCE_SCHEMA_VERSION = "1.0.0"


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class OperatorEvidenceView:
    """Validated read-only summary for one shadow-session parity journal."""

    session_id: str
    status: ShadowSessionStatus
    journal_path: str
    journal_sha256: str
    selection_hash: str
    recovery_snapshot_hash: str
    record_count: int
    cycle_count: int
    match_count: int
    mismatch_count: int
    first_event_time: str
    last_event_time: str
    first_record_hash: str
    last_record_hash: str
    signal_counts: Mapping[str, int]
    option_side_counts: Mapping[str, int]
    runtime_status_counts: Mapping[str, int]
    observation_hashes: tuple[str, ...]
    schema_version: str = OPERATOR_EVIDENCE_SCHEMA_VERSION
    runtime_connected: bool = False
    runtime_cutover_performed: bool = False
    state_written: bool = False
    ledger_written: bool = False
    broker_execution_performed: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != OPERATOR_EVIDENCE_SCHEMA_VERSION:
            raise OperatorEvidenceViewError(
                "unsupported operator evidence schema version"
            )
        if self.record_count < 2:
            raise OperatorEvidenceViewError(
                "operator view requires a started session journal"
            )
        if self.cycle_count != self.match_count + self.mismatch_count:
            raise OperatorEvidenceViewError(
                "cycle count does not equal match plus mismatch counts"
            )
        if (
            self.runtime_connected
            or self.runtime_cutover_performed
            or self.state_written
            or self.ledger_written
            or self.broker_execution_performed
        ):
            raise OperatorEvidenceViewError(
                "operator view contains forbidden lifecycle flags"
            )
        object.__setattr__(self, "signal_counts", _freeze(self.signal_counts))
        object.__setattr__(
            self,
            "option_side_counts",
            _freeze(self.option_side_counts),
        )
        object.__setattr__(
            self,
            "runtime_status_counts",
            _freeze(self.runtime_status_counts),
        )
        object.__setattr__(
            self,
            "observation_hashes",
            tuple(self.observation_hashes),
        )

    @property
    def overall_status(self) -> str:
        if self.mismatch_count:
            return "ATTENTION_MISMATCH"
        if self.status is ShadowSessionStatus.CLOSED:
            return "PASS_CLOSED"
        if self.status is ShadowSessionStatus.HALTED:
            return "ATTENTION_HALTED"
        return "IN_PROGRESS"

    @property
    def view_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "status": self.status.value,
            "overall_status": self.overall_status,
            "journal_path": self.journal_path,
            "journal_sha256": self.journal_sha256,
            "selection_hash": self.selection_hash,
            "recovery_snapshot_hash": self.recovery_snapshot_hash,
            "record_count": self.record_count,
            "cycle_count": self.cycle_count,
            "match_count": self.match_count,
            "mismatch_count": self.mismatch_count,
            "first_event_time": self.first_event_time,
            "last_event_time": self.last_event_time,
            "first_record_hash": self.first_record_hash,
            "last_record_hash": self.last_record_hash,
            "signal_counts": dict(self.signal_counts),
            "option_side_counts": dict(self.option_side_counts),
            "runtime_status_counts": dict(self.runtime_status_counts),
            "observation_hashes": list(self.observation_hashes),
            "runtime_connected": False,
            "runtime_cutover_performed": False,
            "state_written": False,
            "ledger_written": False,
            "broker_execution_performed": False,
        }
        if include_hash:
            payload["view_hash"] = self.view_hash
        return payload

    def render_markdown(self) -> str:
        signal_text = ", ".join(
            f"{key}={value}" for key, value in sorted(self.signal_counts.items())
        ) or "none"
        side_text = ", ".join(
            f"{key}={value}"
            for key, value in sorted(self.option_side_counts.items())
        ) or "none"
        runtime_text = ", ".join(
            f"{key}={value}"
            for key, value in sorted(self.runtime_status_counts.items())
        ) or "none"
        return (
            "# HQE Multi-Strategy Shadow Evidence\n\n"
            f"- Overall status: **{self.overall_status}**\n"
            f"- Session: `{self.session_id}` ({self.status.value})\n"
            f"- Cycles: {self.cycle_count}\n"
            f"- Matches: {self.match_count}\n"
            f"- Mismatches: {self.mismatch_count}\n"
            f"- Signals: {signal_text}\n"
            f"- Option sides: {side_text}\n"
            f"- Runtime observations: {runtime_text}\n"
            f"- Selection hash: `{self.selection_hash}`\n"
            f"- Recovery snapshot: `{self.recovery_snapshot_hash}`\n"
            f"- Journal SHA-256: `{self.journal_sha256}`\n"
            f"- Evidence view hash: `{self.view_hash}`\n\n"
            "## Safety\n\n"
            "- Canonical runtime connected: **NO**\n"
            "- Runtime cutover performed: **NO**\n"
            "- Strategy state written: **NO**\n"
            "- Trading ledger written: **NO**\n"
            "- Broker execution performed: **NO**\n"
        )


class OperatorEvidenceViewReader:
    """Validate a parity journal and build an operator-safe read-only view."""

    def __init__(
        self,
        journal_path: str | Path,
        *,
        strategy_namespace: str | Path | None = None,
    ) -> None:
        self.journal_path = Path(journal_path).resolve(strict=False)
        if strategy_namespace is not None and _is_within(
            Path(strategy_namespace), self.journal_path
        ):
            raise OperatorEvidenceViewError(
                "operator evidence journal must be outside strategy namespace"
            )

    def read(self) -> OperatorEvidenceView:
        if not self.journal_path.is_file():
            raise OperatorEvidenceViewError(
                "operator evidence journal does not exist"
            )
        before = hashlib.sha256(self.journal_path.read_bytes()).hexdigest()
        records = ParityEvidenceJournal(self.journal_path).read_records()
        after = hashlib.sha256(self.journal_path.read_bytes()).hexdigest()
        if before != after:
            raise OperatorEvidenceViewError(
                "parity journal changed during operator read"
            )
        if not records:
            raise OperatorEvidenceViewError("parity journal is empty")
        first = records[0]
        last = records[-1]
        if first.event_type is not ParityEvidenceEventType.SESSION_STARTED:
            raise OperatorEvidenceViewError(
                "operator evidence session has no start record"
            )

        status = ShadowSessionStatus.RUNNING
        if last.event_type is ParityEvidenceEventType.SESSION_CLOSED:
            prior = str(last.details.get("prior_status", "RUNNING"))
            status = (
                ShadowSessionStatus.HALTED
                if prior == ShadowSessionStatus.HALTED.value
                else ShadowSessionStatus.CLOSED
            )
        elif any(
            record.event_type is ParityEvidenceEventType.PARITY_MISMATCH
            for record in records
        ):
            status = ShadowSessionStatus.HALTED

        selection_hashes = {record.selection_hash for record in records}
        recovery_hashes = {
            record.recovery_snapshot_hash for record in records
        }
        if len(selection_hashes) != 1 or len(recovery_hashes) != 1:
            raise OperatorEvidenceViewError(
                "journal identity changed within one session"
            )

        parity_records = tuple(
            record
            for record in records
            if record.event_type
            in {
                ParityEvidenceEventType.PARITY_MATCH,
                ParityEvidenceEventType.PARITY_MISMATCH,
            }
        )
        signals: Counter[str] = Counter()
        sides: Counter[str] = Counter()
        runtime_statuses: Counter[str] = Counter()
        observation_hashes: list[str] = []
        for record in parity_records:
            signal = str(record.details.get("signal", "UNKNOWN"))
            side = str(record.details.get("option_side", "UNKNOWN"))
            signals[signal] += 1
            sides[side] += 1
            runtime_status = str(
                record.details.get("runtime_status_observed", "NOT_RECORDED")
            )
            runtime_statuses[runtime_status] += 1
            observation_hash = str(
                record.details.get("runtime_observation_hash", "")
            )
            if observation_hash:
                observation_hashes.append(observation_hash)

        return OperatorEvidenceView(
            session_id=first.session_id,
            status=status,
            journal_path=str(self.journal_path),
            journal_sha256=before,
            selection_hash=first.selection_hash,
            recovery_snapshot_hash=first.recovery_snapshot_hash,
            record_count=len(records),
            cycle_count=len(parity_records),
            match_count=sum(
                record.event_type is ParityEvidenceEventType.PARITY_MATCH
                for record in parity_records
            ),
            mismatch_count=sum(
                record.event_type is ParityEvidenceEventType.PARITY_MISMATCH
                for record in parity_records
            ),
            first_event_time=first.event_time,
            last_event_time=last.event_time,
            first_record_hash=first.record_hash,
            last_record_hash=last.record_hash,
            signal_counts=dict(signals),
            option_side_counts=dict(sides),
            runtime_status_counts=dict(runtime_statuses),
            observation_hashes=tuple(observation_hashes),
        )
