"""Reviewed flat-state copy into isolated namespaced dry-run storage.

Phase 4C can copy a *READY_FLAT* legacy Module 131 snapshot into an isolated
offline namespace. It never modifies the source, never connects to the
canonical runtime, never activates a selection, and never cuts over runtime
ownership.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.errors import FlatStateMigrationError
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.migration import (
    LegacyFileEvidence,
    LegacyMigrationPlan,
    MigrationReadiness,
)
from src.multi_strategy.selection import (
    SelectionActivationStatus,
    StrategySelectionSnapshot,
)
from src.multi_strategy.storage import (
    DisabledStrategyArtifactStore,
    PositionLifecycle,
    StrategyArtifactPaths,
    StrategyLedgerRow,
    StrategyStateSnapshot,
)

FLAT_COPY_SCHEMA_VERSION = "1.0.0"
LEGACY_ARCHIVE_DIRECTORY = "legacy_source"


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise FlatStateMigrationError(
            f"unable to hash migration artifact: {path}"
        ) from exc


def _is_relative_to(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def _assert_disjoint(source_root: Path, target_root: Path) -> None:
    source = source_root.resolve(strict=False)
    target = target_root.resolve(strict=False)
    if (
        source == target
        or _is_relative_to(target, source)
        or _is_relative_to(source, target)
    ):
        raise FlatStateMigrationError(
            "source and isolated target roots must be disjoint"
        )


def _assert_source_matches_plan(plan: LegacyMigrationPlan) -> None:
    for label, expected in plan.evidence.items():
        current = LegacyFileEvidence.inspect(expected.path)
        if current.to_dict() != expected.to_dict():
            raise FlatStateMigrationError(
                f"legacy source evidence changed after planning: {label}"
            )


def _copy_source_evidence(
    plan: LegacyMigrationPlan,
    destination: Path,
) -> Mapping[str, str]:
    hashes: dict[str, str] = {}
    destination.mkdir(parents=True, exist_ok=False)
    for label, evidence in sorted(plan.evidence.items()):
        if not evidence.exists:
            continue
        source = Path(evidence.path)
        target = destination / source.name
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise FlatStateMigrationError(
                f"unable to read legacy source during copy: {source}"
            ) from exc
        digest = hashlib.sha256(data).hexdigest()
        if digest != evidence.sha256 or len(data) != evidence.size_bytes:
            raise FlatStateMigrationError(
                f"legacy source changed during copy: {label}"
            )
        target.write_bytes(data)
        if _sha256(target) != evidence.sha256:
            raise FlatStateMigrationError(
                f"copied legacy evidence hash mismatch: {label}"
            )
        hashes[f"legacy_source/{source.name}"] = evidence.sha256
    return MappingProxyType(hashes)


def _legacy_ledger_rows(
    plan: LegacyMigrationPlan,
    selection: StrategySelectionSnapshot,
) -> tuple[StrategyLedgerRow, ...]:
    evidence = plan.evidence.get("ledger")
    if evidence is None or not evidence.exists:
        return ()

    path = Path(evidence.path)
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error) as exc:
        raise FlatStateMigrationError(
            f"unable to read legacy ledger for copy: {path}"
        ) from exc

    if len(rows) != len(plan.ledger.row_hashes):
        raise FlatStateMigrationError(
            "legacy ledger row count changed after planning"
        )

    converted: list[StrategyLedgerRow] = []
    for index, (raw, row_hash) in enumerate(
        zip(rows, plan.ledger.row_hashes, strict=True),
        start=1,
    ):
        normalized = {
            str(key): str(value or "")
            for key, value in raw.items()
            if key is not None
        }
        if canonical_mapping_hash(normalized) != row_hash:
            raise FlatStateMigrationError(
                f"legacy ledger row {index} changed after planning"
            )

        event = normalized.get("event", "").strip().upper()
        lifecycle = (
            PositionLifecycle.OPEN
            if event == "POSITION_OPENED"
            else PositionLifecycle.CLOSED
        )
        try:
            price = float(normalized.get("entry", ""))
            paper_pnl = float(normalized.get("paper_pnl", ""))
        except ValueError as exc:
            raise FlatStateMigrationError(
                f"legacy ledger row {index} has invalid numeric data"
            ) from exc

        exit_reason = normalized.get("exit_reason", "").strip().upper()
        reason_code = (
            "LEGACY_POSITION_OPENED"
            if lifecycle is PositionLifecycle.OPEN
            else f"LEGACY_{exit_reason or 'POSITION_CLOSED'}"
        )
        converted.append(
            StrategyLedgerRow.from_selection(
                selection,
                event_id=f"legacy-{index:06d}-{row_hash[:16]}",
                event_time=normalized.get("timestamp", ""),
                lifecycle=lifecycle,
                option_side=normalized.get("side", "").strip().upper(),
                option_symbol=normalized.get(
                    "option_symbol", ""
                ).strip(),
                quantity=0,
                price=price,
                realized_pnl=(
                    None
                    if lifecycle is PositionLifecycle.OPEN
                    else paper_pnl
                ),
                reason_code=reason_code,
            )
        )
    return tuple(converted)


@dataclass(frozen=True)
class FlatStateCopyAuthorization:
    """Explicit authorization for isolated Phase 4C copy only."""

    plan_hash: str
    selection_hash: str
    runtime_confirmed_stopped: bool
    isolated_storage_confirmed: bool
    dry_run_only: bool = True
    runtime_connected: bool = False
    runtime_cutover_allowed: bool = False
    source_modification_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.plan_hash or not self.selection_hash:
            raise FlatStateMigrationError(
                "copy authorization requires plan and selection identity"
            )
        if not self.runtime_confirmed_stopped:
            raise FlatStateMigrationError(
                "explicit runtime-stopped confirmation is required"
            )
        if not self.isolated_storage_confirmed:
            raise FlatStateMigrationError(
                "explicit isolated-storage confirmation is required"
            )
        if not self.dry_run_only:
            raise FlatStateMigrationError(
                "Phase 4C authorization must remain dry-run-only"
            )
        if self.runtime_connected or self.runtime_cutover_allowed:
            raise FlatStateMigrationError(
                "Phase 4C cannot connect or cut over canonical runtime"
            )
        if self.source_modification_allowed:
            raise FlatStateMigrationError(
                "Phase 4C cannot authorize source modification"
            )

    @classmethod
    def from_plan(
        cls,
        plan: LegacyMigrationPlan,
        selection: StrategySelectionSnapshot,
        *,
        runtime_confirmed_stopped: bool,
        isolated_storage_confirmed: bool,
    ) -> "FlatStateCopyAuthorization":
        if plan.selection_hash != selection.selection_hash:
            raise FlatStateMigrationError(
                "migration plan does not match copy selection"
            )
        return cls(
            plan_hash=plan.plan_hash,
            selection_hash=selection.selection_hash,
            runtime_confirmed_stopped=runtime_confirmed_stopped,
            isolated_storage_confirmed=isolated_storage_confirmed,
        )


@dataclass(frozen=True)
class FlatStateCopyResult:
    """Immutable evidence for one completed isolated flat-state copy."""

    plan_hash: str
    selection_hash: str
    source_root: str
    target_root: str
    namespace_directory: str
    copied_source_files: Mapping[str, str]
    destination_hashes: Mapping[str, str]
    converted_ledger_rows: int
    state: StrategyStateSnapshot
    schema_version: str = FLAT_COPY_SCHEMA_VERSION
    migration_complete: bool = True
    dry_run_only: bool = True
    runtime_connected: bool = False
    runtime_cutover_performed: bool = False
    source_modified: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != FLAT_COPY_SCHEMA_VERSION:
            raise FlatStateMigrationError(
                "unsupported flat-copy schema version"
            )
        if not self.migration_complete:
            raise FlatStateMigrationError(
                "completed flat-copy result must mark migration complete"
            )
        if not self.dry_run_only:
            raise FlatStateMigrationError(
                "Phase 4C result must remain dry-run-only"
            )
        if self.runtime_connected or self.runtime_cutover_performed:
            raise FlatStateMigrationError(
                "Phase 4C result cannot connect or cut over runtime"
            )
        if self.source_modified:
            raise FlatStateMigrationError(
                "Phase 4C result cannot report source modification"
            )
        if self.state.lifecycle is not PositionLifecycle.FLAT:
            raise FlatStateMigrationError(
                "Phase 4C can only complete a FLAT state copy"
            )
        if not self.state.migration_complete:
            raise FlatStateMigrationError(
                "copied state must mark migration complete"
            )
        if self.state.selection_hash != self.selection_hash:
            raise FlatStateMigrationError(
                "copied state selection identity mismatch"
            )
        object.__setattr__(
            self,
            "copied_source_files",
            _freeze(self.copied_source_files),
        )
        object.__setattr__(
            self,
            "destination_hashes",
            _freeze(self.destination_hashes),
        )

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_hash": self.plan_hash,
            "selection_hash": self.selection_hash,
            "source_root": self.source_root,
            "target_root": self.target_root,
            "namespace_directory": self.namespace_directory,
            "copied_source_files": dict(self.copied_source_files),
            "destination_hashes": dict(self.destination_hashes),
            "converted_ledger_rows": self.converted_ledger_rows,
            "state": self.state.to_dict(),
            "migration_complete": self.migration_complete,
            "dry_run_only": self.dry_run_only,
            "runtime_connected": self.runtime_connected,
            "runtime_cutover_performed": self.runtime_cutover_performed,
            "source_modified": self.source_modified,
        }

    @property
    def result_hash(self) -> str:
        return canonical_mapping_hash(self._hash_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._hash_payload(),
            "result_hash": self.result_hash,
        }


class ReviewedFlatStateCopyExecutor:
    """Copy one reviewed READY_FLAT plan into an isolated offline namespace."""

    def __init__(
        self,
        target_root: str | Path,
        *,
        isolated_storage_confirmed: bool,
        runtime_connected: bool = False,
    ) -> None:
        if runtime_connected:
            raise FlatStateMigrationError(
                "Phase 4C executor cannot connect to canonical runtime"
            )
        if not isolated_storage_confirmed:
            raise FlatStateMigrationError(
                "Phase 4C executor requires isolated storage confirmation"
            )
        self.target_root = Path(target_root).resolve(strict=False)
        self.isolated_storage_confirmed = True
        self.runtime_connected = False

    def execute(
        self,
        plan: LegacyMigrationPlan,
        selection: StrategySelectionSnapshot,
        authorization: FlatStateCopyAuthorization,
    ) -> FlatStateCopyResult:
        if plan.readiness is not MigrationReadiness.READY_FLAT:
            raise FlatStateMigrationError(
                "flat-state copy requires READY_FLAT migration plan"
            )
        if plan.proposed_state.lifecycle is not PositionLifecycle.FLAT:
            raise FlatStateMigrationError(
                "flat-state copy refuses non-FLAT proposed state"
            )
        if plan.selection_hash != selection.selection_hash:
            raise FlatStateMigrationError(
                "migration plan does not match copy selection"
            )
        if selection.activation_status is not SelectionActivationStatus.DISABLED:
            raise FlatStateMigrationError(
                "copy selection must remain DISABLED"
            )
        if selection.runtime_connected:
            raise FlatStateMigrationError(
                "copy selection cannot be runtime-connected"
            )
        if authorization.plan_hash != plan.plan_hash:
            raise FlatStateMigrationError(
                "copy authorization does not match migration plan"
            )
        if authorization.selection_hash != selection.selection_hash:
            raise FlatStateMigrationError(
                "copy authorization does not match selection"
            )
        if not authorization.runtime_confirmed_stopped:
            raise FlatStateMigrationError(
                "runtime-stopped confirmation is required"
            )
        if not authorization.isolated_storage_confirmed:
            raise FlatStateMigrationError(
                "isolated-storage confirmation is required"
            )
        if not authorization.dry_run_only:
            raise FlatStateMigrationError(
                "copy authorization must remain dry-run-only"
            )

        source_root = Path(plan.source_root).resolve(strict=False)
        _assert_disjoint(source_root, self.target_root)
        _assert_source_matches_plan(plan)

        final_paths = StrategyArtifactPaths.from_selection(
            self.target_root,
            selection,
        )
        if final_paths.namespace_directory.exists():
            raise FlatStateMigrationError(
                "destination strategy namespace already exists"
            )

        final_parent = final_paths.namespace_directory.parent
        final_parent.mkdir(parents=True, exist_ok=True)
        stage_root = final_parent / (
            f".{selection.parameters_hash}.phase4c-{uuid.uuid4().hex}.tmp"
        )
        if stage_root.exists():
            raise FlatStateMigrationError(
                "unexpected migration staging path already exists"
            )

        try:
            store = DisabledStrategyArtifactStore(stage_root)
            staged_paths = store.paths_for(selection)
            store.write_selection(selection)

            completed_state = StrategyStateSnapshot.from_selection(
                selection,
                lifecycle=PositionLifecycle.FLAT,
                last_event_id=plan.proposed_state.last_event_id,
                migration_complete=True,
            )
            store.write_state(selection, completed_state)

            converted_rows = _legacy_ledger_rows(plan, selection)
            for row in converted_rows:
                store.append_ledger_row(selection, row)

            staged_paths.recovery.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            recovery_payload = {
                "schema_version": FLAT_COPY_SCHEMA_VERSION,
                "plan_hash": plan.plan_hash,
                "selection_hash": selection.selection_hash,
                "state": completed_state.to_dict(),
                "source_state_sha256": (
                    plan.evidence["state"].sha256
                    if "state" in plan.evidence
                    else ""
                ),
                "source_ledger_sha256": (
                    plan.evidence["ledger"].sha256
                    if "ledger" in plan.evidence
                    else ""
                ),
                "migration_complete": True,
                "dry_run_only": True,
                "runtime_connected": False,
                "runtime_cutover_performed": False,
            }
            _atomic_write_json(staged_paths.recovery, recovery_payload)

            copied_hashes = _copy_source_evidence(
                plan,
                staged_paths.namespace_directory
                / LEGACY_ARCHIVE_DIRECTORY,
            )

            destination_hashes: dict[str, str] = {}
            for label, path in (
                ("selection.json", staged_paths.selection),
                ("state.json", staged_paths.state),
                ("ledger.csv", staged_paths.ledger),
                ("recovery.json", staged_paths.recovery),
            ):
                if path.is_file():
                    destination_hashes[label] = _sha256(path)

            result = FlatStateCopyResult(
                plan_hash=plan.plan_hash,
                selection_hash=selection.selection_hash,
                source_root=str(source_root),
                target_root=str(self.target_root),
                namespace_directory=str(
                    final_paths.namespace_directory
                ),
                copied_source_files=copied_hashes,
                destination_hashes=destination_hashes,
                converted_ledger_rows=len(converted_rows),
                state=completed_state,
            )
            _atomic_write_json(staged_paths.migration, result.to_dict())

            _assert_source_matches_plan(plan)
            os.replace(
                staged_paths.namespace_directory,
                final_paths.namespace_directory,
            )

            # Remove only the now-empty Phase 4C staging parents.
            try:
                shutil.rmtree(stage_root)
            except FileNotFoundError:
                pass

            for relative, expected_hash in result.destination_hashes.items():
                actual_path = final_paths.namespace_directory / relative
                if _sha256(actual_path) != expected_hash:
                    raise FlatStateMigrationError(
                        f"final copied artifact hash mismatch: {relative}"
                    )
            for relative, expected_hash in result.copied_source_files.items():
                actual_path = final_paths.namespace_directory / relative
                if _sha256(actual_path) != expected_hash:
                    raise FlatStateMigrationError(
                        f"final legacy archive hash mismatch: {relative}"
                    )
            if not final_paths.migration.is_file():
                raise FlatStateMigrationError(
                    "final migration evidence is missing"
                )
            _assert_source_matches_plan(plan)
            return result
        except Exception:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)
            if final_paths.namespace_directory.exists():
                # A post-rename verification failure must not leave an
                # unreviewed partial dry-run namespace behind.
                shutil.rmtree(
                    final_paths.namespace_directory,
                    ignore_errors=True,
                )
            raise
