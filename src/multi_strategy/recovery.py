"""Offline restart-recovery validation for namespaced HQE strategy artifacts.

The reader is intentionally read-only and cannot connect to or update the
canonical product runtime. It validates a completed Phase 4C dry-run namespace
as restart evidence only.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.errors import RestartRecoveryError
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.migration_copy import FLAT_COPY_SCHEMA_VERSION
from src.multi_strategy.selection import (
    SelectionActivationStatus,
    StrategySelectionSnapshot,
)
from src.multi_strategy.storage import (
    LEDGER_COLUMNS,
    LEDGER_SCHEMA_VERSION,
    PositionLifecycle,
    StrategyArtifactPaths,
    StrategyLedgerRow,
    StrategyStateSnapshot,
)

OFFLINE_RECOVERY_SCHEMA_VERSION = "1.0.0"


class OfflineRecoveryReadiness(str, Enum):
    """Only a complete, identity-locked FLAT namespace is recoverable."""

    READY_FLAT = "READY_FLAT"


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def _stable_bytes(path: Path) -> bytes:
    """Read a file only when size and timestamp remain stable."""

    try:
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise RestartRecoveryError(
            f"unable to read recovery artifact: {path}"
        ) from exc
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or len(data) != after.st_size
    ):
        raise RestartRecoveryError(
            f"recovery artifact changed while being read: {path}"
        )
    return data


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json_object(path: Path, label: str) -> tuple[dict[str, Any], str]:
    data = _stable_bytes(path)
    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RestartRecoveryError(
            f"{label} is not valid JSON: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise RestartRecoveryError(f"{label} must be a JSON object")
    return payload, _sha256_bytes(data)


def _optional_float(value: str, label: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise RestartRecoveryError(
            f"ledger {label} must be numeric"
        ) from exc


def _read_ledger(
    path: Path,
    selection: StrategySelectionSnapshot,
) -> tuple[tuple[StrategyLedgerRow, ...], str]:
    if not path.exists():
        return (), ""

    data = _stable_bytes(path)
    try:
        text = data.decode("utf-8-sig")
        reader = csv.DictReader(text.splitlines())
        if tuple(reader.fieldnames or ()) != LEDGER_COLUMNS:
            raise RestartRecoveryError(
                "namespaced ledger header does not match schema"
            )
        raw_rows = [dict(row) for row in reader]
    except (UnicodeError, csv.Error) as exc:
        raise RestartRecoveryError(
            f"unable to parse namespaced ledger: {path}"
        ) from exc

    rows: list[StrategyLedgerRow] = []
    seen: set[str] = set()
    open_position = False
    for index, raw in enumerate(raw_rows, start=1):
        try:
            lifecycle = PositionLifecycle(str(raw.get("lifecycle", "")))
            quantity = int(str(raw.get("quantity", "0")))
        except (ValueError, TypeError) as exc:
            raise RestartRecoveryError(
                f"ledger row {index} has invalid lifecycle or quantity"
            ) from exc

        try:
            row = StrategyLedgerRow(
                ledger_schema_version=str(
                    raw.get("ledger_schema_version", "")
                ),
                event_id=str(raw.get("event_id", "")),
                event_time=str(raw.get("event_time", "")),
                strategy_id=str(raw.get("strategy_id", "")),
                strategy_version=str(raw.get("strategy_version", "")),
                selection_hash=str(raw.get("selection_hash", "")),
                parameters_hash=str(raw.get("parameters_hash", "")),
                lifecycle=lifecycle,
                option_side=str(raw.get("option_side", "")),
                option_symbol=str(raw.get("option_symbol", "")),
                quantity=quantity,
                price=_optional_float(raw.get("price", ""), "price"),
                realized_pnl=_optional_float(
                    raw.get("realized_pnl", ""),
                    "realized_pnl",
                ),
                reason_code=str(raw.get("reason_code", "")),
            )
        except ValueError as exc:
            raise RestartRecoveryError(
                f"ledger row {index} is invalid"
            ) from exc
        if row.ledger_schema_version != LEDGER_SCHEMA_VERSION:
            raise RestartRecoveryError(
                f"ledger row {index} uses unsupported schema"
            )
        if not row.matches_selection(selection):
            raise RestartRecoveryError(
                f"ledger row {index} identity does not match selection"
            )
        if row.event_id in seen:
            raise RestartRecoveryError(
                f"duplicate ledger event_id '{row.event_id}'"
            )
        seen.add(row.event_id)

        if lifecycle is PositionLifecycle.OPEN:
            if open_position:
                raise RestartRecoveryError(
                    "ledger contains overlapping OPEN positions"
                )
            open_position = True
        elif lifecycle is PositionLifecycle.HELD:
            if not open_position:
                raise RestartRecoveryError(
                    "ledger contains HELD without an OPEN position"
                )
        elif lifecycle in {
            PositionLifecycle.CLOSED,
            PositionLifecycle.FLAT,
        }:
            if lifecycle is PositionLifecycle.CLOSED and not open_position:
                raise RestartRecoveryError(
                    "ledger contains CLOSED without an OPEN position"
                )
            open_position = False
        rows.append(row)

    if open_position:
        raise RestartRecoveryError(
            "FLAT recovery namespace contains an unmatched OPEN position"
        )
    return tuple(rows), _sha256_bytes(data)


def _validate_migration_result_hash(payload: Mapping[str, Any]) -> None:
    supplied = str(payload.get("result_hash", ""))
    if not supplied:
        raise RestartRecoveryError(
            "migration evidence is missing result_hash"
        )
    hash_payload = dict(payload)
    hash_payload.pop("result_hash", None)
    if canonical_mapping_hash(hash_payload) != supplied:
        raise RestartRecoveryError(
            "migration result_hash does not match migration evidence"
        )


@dataclass(frozen=True)
class OfflineRestartRecoverySnapshot:
    """Immutable read-only restart evidence for one namespaced strategy."""

    selection: StrategySelectionSnapshot
    state: StrategyStateSnapshot
    ledger_rows: tuple[StrategyLedgerRow, ...]
    recovery_payload: Mapping[str, Any]
    migration_payload: Mapping[str, Any]
    artifact_hashes: Mapping[str, str]
    namespace_directory: str
    readiness: OfflineRecoveryReadiness = (
        OfflineRecoveryReadiness.READY_FLAT
    )
    schema_version: str = OFFLINE_RECOVERY_SCHEMA_VERSION
    runtime_connected: bool = False
    runtime_cutover_performed: bool = False
    source_modified: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != OFFLINE_RECOVERY_SCHEMA_VERSION:
            raise RestartRecoveryError(
                "unsupported offline recovery schema version"
            )
        if self.readiness is not OfflineRecoveryReadiness.READY_FLAT:
            raise RestartRecoveryError(
                "offline recovery snapshot must be READY_FLAT"
            )
        if self.runtime_connected or self.runtime_cutover_performed:
            raise RestartRecoveryError(
                "offline recovery cannot connect or cut over runtime"
            )
        if self.source_modified:
            raise RestartRecoveryError(
                "offline recovery cannot modify source evidence"
            )
        if self.selection.activation_status is not (
            SelectionActivationStatus.DISABLED
        ):
            raise RestartRecoveryError(
                "offline recovery selection must remain DISABLED"
            )
        if self.selection.runtime_connected:
            raise RestartRecoveryError(
                "offline recovery selection cannot be runtime-connected"
            )
        if not self.state.matches_selection(self.selection):
            raise RestartRecoveryError(
                "offline recovery state identity mismatch"
            )
        if self.state.lifecycle is not PositionLifecycle.FLAT:
            raise RestartRecoveryError(
                "Phase 4D recovery supports FLAT state only"
            )
        if not self.state.migration_complete:
            raise RestartRecoveryError(
                "offline recovery requires completed migration evidence"
            )
        object.__setattr__(
            self,
            "recovery_payload",
            _freeze(self.recovery_payload),
        )
        object.__setattr__(
            self,
            "migration_payload",
            _freeze(self.migration_payload),
        )
        object.__setattr__(
            self,
            "artifact_hashes",
            _freeze(self.artifact_hashes),
        )

    @property
    def snapshot_hash(self) -> str:
        return canonical_mapping_hash(
            {
                "schema_version": self.schema_version,
                "readiness": self.readiness.value,
                "selection_hash": self.selection.selection_hash,
                "state": self.state.to_dict(),
                "ledger_event_ids": [
                    row.event_id for row in self.ledger_rows
                ],
                "recovery_payload": dict(self.recovery_payload),
                "migration_payload": dict(self.migration_payload),
                "artifact_hashes": dict(self.artifact_hashes),
                "namespace_directory": self.namespace_directory,
                "runtime_connected": self.runtime_connected,
                "runtime_cutover_performed": (
                    self.runtime_cutover_performed
                ),
                "source_modified": self.source_modified,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "readiness": self.readiness.value,
            "selection": self.selection.to_dict(),
            "state": self.state.to_dict(),
            "ledger_event_count": len(self.ledger_rows),
            "ledger_event_ids": [
                row.event_id for row in self.ledger_rows
            ],
            "recovery_payload": dict(self.recovery_payload),
            "migration_payload": dict(self.migration_payload),
            "artifact_hashes": dict(self.artifact_hashes),
            "namespace_directory": self.namespace_directory,
            "runtime_connected": self.runtime_connected,
            "runtime_cutover_performed": (
                self.runtime_cutover_performed
            ),
            "source_modified": self.source_modified,
            "snapshot_hash": self.snapshot_hash,
        }


class OfflineRestartRecoveryReader:
    """Validate restart evidence without writing or connecting runtime."""

    def __init__(
        self,
        root: str | Path,
        *,
        runtime_connected: bool = False,
    ) -> None:
        if runtime_connected:
            raise RestartRecoveryError(
                "offline recovery reader cannot connect to runtime"
            )
        self.root = Path(root).resolve(strict=False)
        self.runtime_connected = False

    def read(
        self,
        expected_selection: StrategySelectionSnapshot,
    ) -> OfflineRestartRecoverySnapshot:
        paths = StrategyArtifactPaths.from_selection(
            self.root,
            expected_selection,
        )
        if not paths.namespace_directory.is_dir():
            raise RestartRecoveryError(
                "strategy namespace does not exist"
            )

        selection_payload, selection_hash = _read_json_object(
            paths.selection,
            "selection snapshot",
        )
        selection = StrategySelectionSnapshot.from_dict(
            selection_payload
        )
        if selection.selection_hash != expected_selection.selection_hash:
            raise RestartRecoveryError(
                "stored selection does not match expected selection"
            )

        state_payload, state_hash = _read_json_object(
            paths.state,
            "state snapshot",
        )
        state = StrategyStateSnapshot.from_dict(state_payload)
        if not state.matches_selection(selection):
            raise RestartRecoveryError(
                "stored state identity does not match selection"
            )

        ledger_rows, ledger_hash = _read_ledger(
            paths.ledger,
            selection,
        )
        if state.last_event_id:
            if not ledger_rows:
                raise RestartRecoveryError(
                    "state last_event_id exists but ledger is empty"
                )
            final_event_id = ledger_rows[-1].event_id
            legacy_compatibility_event = (
                final_event_id.startswith("legacy-")
                and final_event_id.endswith(
                    state.last_event_id[:16]
                )
            )
            if (
                final_event_id != state.last_event_id
                and not legacy_compatibility_event
            ):
                raise RestartRecoveryError(
                    "state last_event_id does not match final ledger event"
                )
        elif ledger_rows:
            raise RestartRecoveryError(
                "ledger has events but state last_event_id is empty"
            )

        recovery_payload, recovery_hash = _read_json_object(
            paths.recovery,
            "recovery evidence",
        )
        migration_payload, migration_hash = _read_json_object(
            paths.migration,
            "migration evidence",
        )

        if str(recovery_payload.get("schema_version", "")) != (
            FLAT_COPY_SCHEMA_VERSION
        ):
            raise RestartRecoveryError(
                "recovery evidence schema mismatch"
            )
        if recovery_payload.get("state") != state.to_dict():
            raise RestartRecoveryError(
                "recovery evidence state does not match state.json"
            )
        if str(recovery_payload.get("selection_hash", "")) != (
            selection.selection_hash
        ):
            raise RestartRecoveryError(
                "recovery evidence selection_hash mismatch"
            )
        if not bool(recovery_payload.get("migration_complete", False)):
            raise RestartRecoveryError(
                "recovery evidence does not mark migration complete"
            )
        if not bool(recovery_payload.get("dry_run_only", False)):
            raise RestartRecoveryError(
                "recovery evidence must remain dry-run-only"
            )
        if bool(recovery_payload.get("runtime_connected", False)):
            raise RestartRecoveryError(
                "recovery evidence cannot be runtime-connected"
            )
        if bool(
            recovery_payload.get("runtime_cutover_performed", False)
        ):
            raise RestartRecoveryError(
                "recovery evidence cannot report runtime cutover"
            )

        _validate_migration_result_hash(migration_payload)
        if str(migration_payload.get("schema_version", "")) != (
            FLAT_COPY_SCHEMA_VERSION
        ):
            raise RestartRecoveryError(
                "migration evidence schema mismatch"
            )
        if str(migration_payload.get("selection_hash", "")) != (
            selection.selection_hash
        ):
            raise RestartRecoveryError(
                "migration evidence selection_hash mismatch"
            )
        if migration_payload.get("state") != state.to_dict():
            raise RestartRecoveryError(
                "migration evidence state does not match state.json"
            )
        if not bool(migration_payload.get("migration_complete", False)):
            raise RestartRecoveryError(
                "migration evidence does not mark migration complete"
            )
        if not bool(migration_payload.get("dry_run_only", False)):
            raise RestartRecoveryError(
                "migration evidence must remain dry-run-only"
            )
        if bool(migration_payload.get("runtime_connected", False)):
            raise RestartRecoveryError(
                "migration evidence cannot be runtime-connected"
            )
        if bool(
            migration_payload.get("runtime_cutover_performed", False)
        ):
            raise RestartRecoveryError(
                "migration evidence cannot report runtime cutover"
            )
        if bool(migration_payload.get("source_modified", False)):
            raise RestartRecoveryError(
                "migration evidence cannot report source modification"
            )
        if Path(
            str(migration_payload.get("namespace_directory", ""))
        ).resolve(strict=False) != paths.namespace_directory.resolve(
            strict=False
        ):
            raise RestartRecoveryError(
                "migration namespace_directory mismatch"
            )

        actual_hashes = {
            "selection.json": selection_hash,
            "state.json": state_hash,
            "recovery.json": recovery_hash,
            "migration.json": migration_hash,
        }
        if ledger_hash:
            actual_hashes["ledger.csv"] = ledger_hash

        destination_hashes = migration_payload.get(
            "destination_hashes",
            {},
        )
        if not isinstance(destination_hashes, Mapping):
            raise RestartRecoveryError(
                "migration destination_hashes must be a mapping"
            )
        for relative, expected_hash in destination_hashes.items():
            relative_text = str(relative)
            if relative_text not in actual_hashes:
                raise RestartRecoveryError(
                    f"migration references missing artifact '{relative_text}'"
                )
            if actual_hashes[relative_text] != str(expected_hash):
                raise RestartRecoveryError(
                    f"artifact hash mismatch for '{relative_text}'"
                )

        copied_source_files = migration_payload.get(
            "copied_source_files",
            {},
        )
        if not isinstance(copied_source_files, Mapping):
            raise RestartRecoveryError(
                "migration copied_source_files must be a mapping"
            )
        for relative, expected_hash in copied_source_files.items():
            relative_path = paths.namespace_directory / str(relative)
            try:
                relative_path.resolve(strict=False).relative_to(
                    paths.namespace_directory.resolve(strict=False)
                )
            except ValueError as exc:
                raise RestartRecoveryError(
                    "migration legacy archive path escapes namespace"
                ) from exc
            data = _stable_bytes(relative_path)
            actual = _sha256_bytes(data)
            if actual != str(expected_hash):
                raise RestartRecoveryError(
                    f"legacy archive hash mismatch for '{relative}'"
                )
            actual_hashes[str(relative)] = actual

        source_state_hash = str(
            recovery_payload.get("source_state_sha256", "")
        )
        source_ledger_hash = str(
            recovery_payload.get("source_ledger_sha256", "")
        )
        archived_values = set(
            str(value) for value in copied_source_files.values()
        )
        for label, expected in (
            ("source_state_sha256", source_state_hash),
            ("source_ledger_sha256", source_ledger_hash),
        ):
            if expected and expected not in archived_values:
                raise RestartRecoveryError(
                    f"{label} is not present in legacy archive evidence"
                )

        # Double-read all core artifacts to prove the namespace remained
        # unchanged throughout validation.
        for relative, expected_hash in tuple(actual_hashes.items()):
            path = paths.namespace_directory / relative
            if _sha256_bytes(_stable_bytes(path)) != expected_hash:
                raise RestartRecoveryError(
                    f"artifact changed during recovery read: {relative}"
                )

        return OfflineRestartRecoverySnapshot(
            selection=selection,
            state=state,
            ledger_rows=ledger_rows,
            recovery_payload=recovery_payload,
            migration_payload=migration_payload,
            artifact_hashes=actual_hashes,
            namespace_directory=str(paths.namespace_directory),
        )
