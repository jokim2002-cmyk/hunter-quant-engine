"""Tamper-evident lifecycle bundle for the isolated HQE write sandbox.

The bundle is the single authoritative sandbox artifact. It is written with
``os.replace`` and contains the current namespaced state plus a hash-chained
sequence of lifecycle events. It is never connected to the canonical product
runtime or canonical Module 131 lifecycle files.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot

LIFECYCLE_JOURNAL_SCHEMA_VERSION = "1.0.0"
_ALLOWED_TRANSITIONS = {
    "FLAT->OPEN",
    "OPEN->HELD",
    "OPEN->CLOSED",
    "HELD->CLOSED",
    "CLOSED->FLAT",
}


class LifecycleJournalError(ValueError):
    """Raised when a sandbox lifecycle bundle is invalid or tampered."""


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def state_hash(state: StrategyStateSnapshot) -> str:
    return canonical_mapping_hash(state.to_dict())


@dataclass(frozen=True)
class SandboxLifecycleEvent:
    """One immutable hash-chained lifecycle event."""

    event_id: str
    event_time: str
    strategy_id: str
    strategy_version: str
    selection_hash: str
    before_state_hash: str
    after_state: Mapping[str, Any]
    transition: str
    option_side: str
    option_symbol: str
    quantity: int
    price: float | None
    realized_pnl: float | None
    reason_code: str
    previous_event_hash: str = ""
    schema_version: str = LIFECYCLE_JOURNAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != LIFECYCLE_JOURNAL_SCHEMA_VERSION:
            raise LifecycleJournalError("unsupported lifecycle event schema")
        if not self.event_id or not self.event_time:
            raise LifecycleJournalError("event identity is required")
        if not self.strategy_id or not self.strategy_version:
            raise LifecycleJournalError("strategy identity is required")
        if not self.selection_hash or not self.before_state_hash:
            raise LifecycleJournalError("selection and before-state hashes are required")
        if self.transition not in _ALLOWED_TRANSITIONS:
            raise LifecycleJournalError("unsupported lifecycle event transition")
        if self.option_side not in {"CE_BUY", "PE_BUY", "NO_TRADE"}:
            raise LifecycleJournalError("invalid lifecycle event option_side")
        if not isinstance(self.quantity, int) or self.quantity < 0:
            raise LifecycleJournalError("quantity must be a non-negative integer")
        object.__setattr__(self, "after_state", _freeze(self.after_state))
        after = StrategyStateSnapshot.from_dict(self.after_state)
        if after.strategy_id != self.strategy_id:
            raise LifecycleJournalError("after-state strategy_id mismatch")
        if after.strategy_version != self.strategy_version:
            raise LifecycleJournalError("after-state strategy_version mismatch")
        if after.selection_hash != self.selection_hash:
            raise LifecycleJournalError("after-state selection_hash mismatch")
        expected_transition = self.transition.split("->", 1)[1]
        if after.lifecycle.value != expected_transition:
            raise LifecycleJournalError("after-state lifecycle mismatch")
        if after.last_event_id != self.event_id:
            raise LifecycleJournalError("after-state last_event_id mismatch")

    @property
    def after_state_hash(self) -> str:
        return canonical_mapping_hash(dict(self.after_state))

    @property
    def event_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "event_time": self.event_time,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "selection_hash": self.selection_hash,
            "before_state_hash": self.before_state_hash,
            "after_state_hash": self.after_state_hash,
            "after_state": dict(self.after_state),
            "transition": self.transition,
            "option_side": self.option_side,
            "option_symbol": self.option_symbol,
            "quantity": self.quantity,
            "price": self.price,
            "realized_pnl": self.realized_pnl,
            "reason_code": self.reason_code,
            "previous_event_hash": self.previous_event_hash,
        }
        if include_hash:
            payload["event_hash"] = self.event_hash
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SandboxLifecycleEvent":
        raw_after = payload.get("after_state", {})
        if not isinstance(raw_after, Mapping):
            raise LifecycleJournalError("after_state must be an object")
        event = cls(
            schema_version=str(payload.get("schema_version", "")),
            event_id=str(payload.get("event_id", "")),
            event_time=str(payload.get("event_time", "")),
            strategy_id=str(payload.get("strategy_id", "")),
            strategy_version=str(payload.get("strategy_version", "")),
            selection_hash=str(payload.get("selection_hash", "")),
            before_state_hash=str(payload.get("before_state_hash", "")),
            after_state=dict(raw_after),
            transition=str(payload.get("transition", "")),
            option_side=str(payload.get("option_side", "")),
            option_symbol=str(payload.get("option_symbol", "")),
            quantity=int(payload.get("quantity", 0)),
            price=(None if payload.get("price") is None else float(payload["price"])),
            realized_pnl=(
                None
                if payload.get("realized_pnl") is None
                else float(payload["realized_pnl"])
            ),
            reason_code=str(payload.get("reason_code", "")),
            previous_event_hash=str(payload.get("previous_event_hash", "")),
        )
        supplied_after_hash = str(payload.get("after_state_hash", ""))
        if supplied_after_hash and supplied_after_hash != event.after_state_hash:
            raise LifecycleJournalError("after_state_hash mismatch")
        supplied_event_hash = str(payload.get("event_hash", ""))
        if supplied_event_hash and supplied_event_hash != event.event_hash:
            raise LifecycleJournalError("event_hash mismatch")
        return event


@dataclass(frozen=True)
class SandboxLifecycleBundle:
    """Single-file authoritative lifecycle state for one sandbox namespace."""

    selection: StrategySelectionSnapshot
    current_state: StrategyStateSnapshot
    events: tuple[SandboxLifecycleEvent, ...] = ()
    schema_version: str = LIFECYCLE_JOURNAL_SCHEMA_VERSION
    mode: str = "GUARDED_NAMESPACED_LIFECYCLE_WRITE_SANDBOX"
    canonical_runtime_connected: bool = False
    canonical_state_written: bool = False
    canonical_ledger_written: bool = False
    broker_execution_performed: bool = False
    real_money_used: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != LIFECYCLE_JOURNAL_SCHEMA_VERSION:
            raise LifecycleJournalError("unsupported lifecycle bundle schema")
        if self.mode != "GUARDED_NAMESPACED_LIFECYCLE_WRITE_SANDBOX":
            raise LifecycleJournalError("invalid lifecycle bundle mode")
        if any(
            (
                self.canonical_runtime_connected,
                self.canonical_state_written,
                self.canonical_ledger_written,
                self.broker_execution_performed,
                self.real_money_used,
            )
        ):
            raise LifecycleJournalError("sandbox bundle cannot touch canonical execution")
        if not self.current_state.matches_selection(self.selection):
            raise LifecycleJournalError("bundle state does not match selection")
        previous_hash = ""
        previous_state_hash = ""
        seen: set[str] = set()
        for index, event in enumerate(self.events):
            if event.selection_hash != self.selection.selection_hash:
                raise LifecycleJournalError("event selection mismatch")
            if event.event_id in seen:
                raise LifecycleJournalError("duplicate lifecycle event_id")
            seen.add(event.event_id)
            if event.previous_event_hash != previous_hash:
                raise LifecycleJournalError("lifecycle event hash chain mismatch")
            if index and event.before_state_hash != previous_state_hash:
                raise LifecycleJournalError("lifecycle state hash chain mismatch")
            previous_hash = event.event_hash
            previous_state_hash = event.after_state_hash
        if self.events:
            if self.events[-1].after_state_hash != state_hash(self.current_state):
                raise LifecycleJournalError("current state does not match final event")
        elif self.current_state.lifecycle is not PositionLifecycle.FLAT:
            raise LifecycleJournalError("empty lifecycle bundle must start FLAT")

    @property
    def bundle_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "selection": self.selection.to_dict(),
            "current_state": self.current_state.to_dict(),
            "events": [event.to_dict() for event in self.events],
            "event_count": len(self.events),
            "canonical_runtime_connected": False,
            "canonical_state_written": False,
            "canonical_ledger_written": False,
            "broker_execution_performed": False,
            "real_money_used": False,
        }
        if include_hash:
            payload["bundle_hash"] = self.bundle_hash
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SandboxLifecycleBundle":
        raw_selection = payload.get("selection", {})
        raw_state = payload.get("current_state", {})
        raw_events = payload.get("events", [])
        if not isinstance(raw_selection, Mapping):
            raise LifecycleJournalError("bundle selection must be an object")
        if not isinstance(raw_state, Mapping):
            raise LifecycleJournalError("bundle state must be an object")
        if not isinstance(raw_events, list):
            raise LifecycleJournalError("bundle events must be an array")
        bundle = cls(
            schema_version=str(payload.get("schema_version", "")),
            mode=str(payload.get("mode", "")),
            selection=StrategySelectionSnapshot.from_dict(raw_selection),
            current_state=StrategyStateSnapshot.from_dict(raw_state),
            events=tuple(SandboxLifecycleEvent.from_dict(item) for item in raw_events),
            canonical_runtime_connected=bool(payload.get("canonical_runtime_connected", False)),
            canonical_state_written=bool(payload.get("canonical_state_written", False)),
            canonical_ledger_written=bool(payload.get("canonical_ledger_written", False)),
            broker_execution_performed=bool(payload.get("broker_execution_performed", False)),
            real_money_used=bool(payload.get("real_money_used", False)),
        )
        if int(payload.get("event_count", len(bundle.events))) != len(bundle.events):
            raise LifecycleJournalError("bundle event_count mismatch")
        supplied = str(payload.get("bundle_hash", ""))
        if supplied and supplied != bundle.bundle_hash:
            raise LifecycleJournalError("bundle_hash mismatch")
        return bundle


def read_bundle(path: str | Path) -> SandboxLifecycleBundle:
    target = Path(path)
    try:
        data = target.read_bytes()
        payload = json.loads(data.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LifecycleJournalError(f"unable to read lifecycle bundle: {target}") from exc
    if not isinstance(payload, Mapping):
        raise LifecycleJournalError("lifecycle bundle must be a JSON object")
    return SandboxLifecycleBundle.from_dict(payload)


def write_bundle_atomic(path: str | Path, bundle: SandboxLifecycleBundle) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
    encoded = json.dumps(bundle.to_dict(), indent=2, sort_keys=True) + "\n"
    try:
        temporary.write_text(encoded, encoding="utf-8", newline="\n")
        os.replace(temporary, target)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise LifecycleJournalError(f"unable to write lifecycle bundle: {target}") from exc
    return target


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
