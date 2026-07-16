"""Disabled namespaced state and ledger foundation for HQE strategies.

The store in this module is intentionally offline. It is not connected to the
canonical product paper runtime, Module 131, or the existing product UI.
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.errors import (
    SelectionSwitchBlockedError,
    StrategyStorageError,
)
from src.multi_strategy.selection import StrategySelectionSnapshot

STATE_SCHEMA_VERSION = "1.0.0"
LEDGER_SCHEMA_VERSION = "1.0.0"
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_.+-]+$")
LEDGER_COLUMNS = (
    "ledger_schema_version",
    "event_id",
    "event_time",
    "strategy_id",
    "strategy_version",
    "selection_hash",
    "parameters_hash",
    "lifecycle",
    "option_side",
    "option_symbol",
    "quantity",
    "price",
    "realized_pnl",
    "reason_code",
)


class PositionLifecycle(str, Enum):
    FLAT = "FLAT"
    OPEN = "OPEN"
    HELD = "HELD"
    CLOSED = "CLOSED"

    @property
    def has_open_position(self) -> bool:
        return self in {PositionLifecycle.OPEN, PositionLifecycle.HELD}


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def _require_safe_component(label: str, value: str) -> str:
    text = str(value).strip()
    if not text or not _SAFE_COMPONENT.fullmatch(text):
        raise StrategyStorageError(
            f"{label} contains an unsafe path component"
        )
    if text in {".", ".."}:
        raise StrategyStorageError(f"{label} cannot be '.' or '..'")
    return text


def _ensure_within(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve(strict=False)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise StrategyStorageError(
            "strategy artifact path escapes the configured root"
        ) from exc
    return resolved_candidate


@dataclass(frozen=True)
class StrategyArtifactPaths:
    root: Path
    namespace_directory: Path
    selection: Path
    state: Path
    ledger: Path
    report: Path
    reason_log: Path
    recovery: Path
    migration: Path

    @classmethod
    def from_selection(
        cls,
        root: str | Path,
        selection: StrategySelectionSnapshot,
    ) -> "StrategyArtifactPaths":
        root_path = Path(root).resolve(strict=False)
        strategy_id = _require_safe_component(
            "strategy_id", selection.strategy_id
        )
        strategy_version = _require_safe_component(
            "strategy_version", selection.strategy_version
        )
        parameters_hash = _require_safe_component(
            "parameters_hash", selection.parameters_hash
        )
        namespace = _ensure_within(
            root_path,
            root_path
            / "strategies"
            / strategy_id
            / strategy_version
            / parameters_hash,
        )
        return cls(
            root=root_path,
            namespace_directory=namespace,
            selection=namespace / "selection.json",
            state=namespace / "state.json",
            ledger=namespace / "ledger.csv",
            report=namespace / "report.md",
            reason_log=namespace / "reason_log.csv",
            recovery=namespace / "recovery.json",
            migration=namespace / "migration.json",
        )


@dataclass(frozen=True)
class StrategyStateSnapshot:
    strategy_id: str
    strategy_version: str
    selection_hash: str
    parameters_hash: str
    state_schema_version: str = STATE_SCHEMA_VERSION
    lifecycle: PositionLifecycle = PositionLifecycle.FLAT
    position: Mapping[str, Any] = MappingProxyType({})
    last_event_id: str = ""
    migration_complete: bool = False

    def __post_init__(self) -> None:
        if self.state_schema_version != STATE_SCHEMA_VERSION:
            raise StrategyStorageError("unsupported state_schema_version")
        if not self.strategy_id or not self.strategy_version:
            raise StrategyStorageError("state strategy identity is required")
        if not self.selection_hash or not self.parameters_hash:
            raise StrategyStorageError("state selection identity is required")
        if self.lifecycle.has_open_position and not self.position:
            raise StrategyStorageError(
                "OPEN/HELD state requires position details"
            )
        if self.lifecycle is PositionLifecycle.FLAT and self.position:
            raise StrategyStorageError(
                "FLAT state cannot contain an open position"
            )
        object.__setattr__(self, "position", _freeze(self.position))

    @classmethod
    def from_selection(
        cls,
        selection: StrategySelectionSnapshot,
        *,
        lifecycle: PositionLifecycle = PositionLifecycle.FLAT,
        position: Mapping[str, Any] | None = None,
        last_event_id: str = "",
        migration_complete: bool = False,
    ) -> "StrategyStateSnapshot":
        return cls(
            strategy_id=selection.strategy_id,
            strategy_version=selection.strategy_version,
            selection_hash=selection.selection_hash,
            parameters_hash=selection.parameters_hash,
            lifecycle=lifecycle,
            position=dict(position or {}),
            last_event_id=str(last_event_id),
            migration_complete=bool(migration_complete),
        )

    def matches_selection(
        self,
        selection: StrategySelectionSnapshot,
    ) -> bool:
        return (
            self.strategy_id == selection.strategy_id
            and self.strategy_version == selection.strategy_version
            and self.selection_hash == selection.selection_hash
            and self.parameters_hash == selection.parameters_hash
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_schema_version": self.state_schema_version,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "selection_hash": self.selection_hash,
            "parameters_hash": self.parameters_hash,
            "lifecycle": self.lifecycle.value,
            "position": dict(self.position),
            "last_event_id": self.last_event_id,
            "migration_complete": self.migration_complete,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StrategyStateSnapshot":
        raw_position = payload.get("position", {})
        if not isinstance(raw_position, Mapping):
            raise StrategyStorageError("state position must be a mapping")
        try:
            lifecycle = PositionLifecycle(str(payload.get("lifecycle", "")))
        except ValueError as exc:
            raise StrategyStorageError("invalid position lifecycle") from exc
        return cls(
            state_schema_version=str(
                payload.get("state_schema_version", "")
            ),
            strategy_id=str(payload.get("strategy_id", "")),
            strategy_version=str(payload.get("strategy_version", "")),
            selection_hash=str(payload.get("selection_hash", "")),
            parameters_hash=str(payload.get("parameters_hash", "")),
            lifecycle=lifecycle,
            position=dict(raw_position),
            last_event_id=str(payload.get("last_event_id", "")),
            migration_complete=bool(
                payload.get("migration_complete", False)
            ),
        )


@dataclass(frozen=True)
class StrategyLedgerRow:
    event_id: str
    event_time: str
    strategy_id: str
    strategy_version: str
    selection_hash: str
    parameters_hash: str
    lifecycle: PositionLifecycle
    option_side: str
    option_symbol: str = ""
    quantity: int = 0
    price: float | None = None
    realized_pnl: float | None = None
    reason_code: str = ""
    ledger_schema_version: str = LEDGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.ledger_schema_version != LEDGER_SCHEMA_VERSION:
            raise StrategyStorageError("unsupported ledger_schema_version")
        if not self.event_id or not self.event_time:
            raise StrategyStorageError("ledger event identity is required")
        if self.option_side not in {"CE_BUY", "PE_BUY", "NO_TRADE"}:
            raise StrategyStorageError("invalid ledger option_side")
        if not isinstance(self.quantity, int) or self.quantity < 0:
            raise StrategyStorageError("ledger quantity must be non-negative")

    @classmethod
    def from_selection(
        cls,
        selection: StrategySelectionSnapshot,
        *,
        event_id: str,
        event_time: str,
        lifecycle: PositionLifecycle,
        option_side: str,
        option_symbol: str = "",
        quantity: int = 0,
        price: float | None = None,
        realized_pnl: float | None = None,
        reason_code: str = "",
    ) -> "StrategyLedgerRow":
        return cls(
            event_id=str(event_id),
            event_time=str(event_time),
            strategy_id=selection.strategy_id,
            strategy_version=selection.strategy_version,
            selection_hash=selection.selection_hash,
            parameters_hash=selection.parameters_hash,
            lifecycle=lifecycle,
            option_side=str(option_side),
            option_symbol=str(option_symbol),
            quantity=quantity,
            price=price,
            realized_pnl=realized_pnl,
            reason_code=str(reason_code),
        )

    def matches_selection(
        self,
        selection: StrategySelectionSnapshot,
    ) -> bool:
        return (
            self.strategy_id == selection.strategy_id
            and self.strategy_version == selection.strategy_version
            and self.selection_hash == selection.selection_hash
            and self.parameters_hash == selection.parameters_hash
        )

    def to_csv_dict(self) -> dict[str, str]:
        return {
            "ledger_schema_version": self.ledger_schema_version,
            "event_id": self.event_id,
            "event_time": self.event_time,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "selection_hash": self.selection_hash,
            "parameters_hash": self.parameters_hash,
            "lifecycle": self.lifecycle.value,
            "option_side": self.option_side,
            "option_symbol": self.option_symbol,
            "quantity": str(self.quantity),
            "price": "" if self.price is None else str(self.price),
            "realized_pnl": (
                "" if self.realized_pnl is None else str(self.realized_pnl)
            ),
            "reason_code": self.reason_code,
        }


def assert_strategy_switch_allowed(
    current_selection: StrategySelectionSnapshot,
    requested_selection: StrategySelectionSnapshot,
    current_state: StrategyStateSnapshot,
    *,
    runtime_running: bool,
) -> None:
    """Fail closed unless the current strategy is flat and migrated."""

    if current_selection.selection_hash == requested_selection.selection_hash:
        return
    if not current_state.matches_selection(current_selection):
        raise SelectionSwitchBlockedError(
            "current state identity does not match current selection"
        )
    if runtime_running:
        raise SelectionSwitchBlockedError(
            "cannot switch strategy while runtime is running"
        )
    if current_state.lifecycle.has_open_position:
        raise SelectionSwitchBlockedError(
            "cannot switch strategy while a position is OPEN or HELD"
        )
    if not current_state.migration_complete:
        raise SelectionSwitchBlockedError(
            "cannot switch strategy before state migration is complete"
        )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


class DisabledStrategyArtifactStore:
    """Offline-only namespaced store; runtime connection is prohibited."""

    def __init__(
        self,
        root: str | Path,
        *,
        runtime_connected: bool = False,
    ) -> None:
        if runtime_connected:
            raise StrategyStorageError(
                "Phase 4A store cannot be connected to canonical runtime"
            )
        self.root = Path(root).resolve(strict=False)
        self.runtime_connected = False

    def paths_for(
        self,
        selection: StrategySelectionSnapshot,
    ) -> StrategyArtifactPaths:
        return StrategyArtifactPaths.from_selection(self.root, selection)

    def write_selection(
        self,
        selection: StrategySelectionSnapshot,
    ) -> Path:
        path = self.paths_for(selection).selection
        _atomic_write_text(
            path,
            json.dumps(selection.to_dict(), indent=2, sort_keys=True) + "\n",
        )
        return path

    def read_selection(
        self,
        selection: StrategySelectionSnapshot,
    ) -> StrategySelectionSnapshot:
        path = self.paths_for(selection).selection
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StrategyStorageError(
                f"unable to read selection snapshot: {path}"
            ) from exc
        if not isinstance(payload, Mapping):
            raise StrategyStorageError("selection snapshot must be an object")
        loaded = StrategySelectionSnapshot.from_dict(payload)
        if loaded.selection_hash != selection.selection_hash:
            raise StrategyStorageError(
                "stored selection does not match requested namespace"
            )
        return loaded

    def write_state(
        self,
        selection: StrategySelectionSnapshot,
        state: StrategyStateSnapshot,
    ) -> Path:
        if not state.matches_selection(selection):
            raise StrategyStorageError(
                "state identity does not match selection namespace"
            )
        path = self.paths_for(selection).state
        _atomic_write_text(
            path,
            json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n",
        )
        return path

    def read_state(
        self,
        selection: StrategySelectionSnapshot,
    ) -> StrategyStateSnapshot:
        path = self.paths_for(selection).state
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StrategyStorageError(
                f"unable to read state snapshot: {path}"
            ) from exc
        if not isinstance(payload, Mapping):
            raise StrategyStorageError("state snapshot must be an object")
        state = StrategyStateSnapshot.from_dict(payload)
        if not state.matches_selection(selection):
            raise StrategyStorageError(
                "stored state does not match selection namespace"
            )
        return state

    def append_ledger_row(
        self,
        selection: StrategySelectionSnapshot,
        row: StrategyLedgerRow,
    ) -> Path:
        if not row.matches_selection(selection):
            raise StrategyStorageError(
                "ledger row identity does not match selection namespace"
            )
        path = self.paths_for(selection).ledger
        existing_rows: list[dict[str, str]] = []
        if path.exists():
            try:
                with path.open("r", newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    if tuple(reader.fieldnames or ()) != LEDGER_COLUMNS:
                        raise StrategyStorageError(
                            "existing ledger header does not match schema"
                        )
                    existing_rows = [dict(item) for item in reader]
            except (OSError, csv.Error) as exc:
                raise StrategyStorageError(
                    f"unable to read existing ledger: {path}"
                ) from exc
            if any(item.get("event_id") == row.event_id for item in existing_rows):
                raise StrategyStorageError(
                    f"duplicate ledger event_id '{row.event_id}'"
                )

        all_rows = existing_rows + [row.to_csv_dict()]
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        try:
            with temporary.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(LEDGER_COLUMNS),
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(all_rows)
            os.replace(temporary, path)
        except (OSError, csv.Error) as exc:
            raise StrategyStorageError(
                f"unable to write ledger: {path}"
            ) from exc
        return path
