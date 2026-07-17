"""Parallel isolated paper observation for reviewed HQE strategies.

Phase 7 fans the same normalized recorded-paper input into two or more reviewed
forward-compatible strategy lanes.  Every lane owns a separate state file,
ledger, event chain, summary and P&L.  The module never reads or writes the
canonical Module 131 lifecycle namespace, never changes product selection,
and never places or routes an order.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.contract import ForwardPaperCompatibilityAdapter
from src.multi_strategy.execution import (
    ExecutionMode,
    canonical_mapping_hash,
)
from src.multi_strategy.recorded import (
    RecordedStrategyInput,
    RegisteredRecordedEvaluator,
)
from src.multi_strategy.registry import (
    RegistrationStatus,
    StrategyRegistry,
)

PARALLEL_OBSERVATION_SCHEMA_VERSION = "1.0.0"
OBSERVATION_FOLDER = "HQE_MULTI_STRATEGY_PARALLEL_OBSERVATION"
SESSION_MANIFEST_FILE = "SESSION_MANIFEST.json"
SESSION_SUMMARY_FILE = "SESSION_SUMMARY.json"
SESSION_EVENTS_FILE = "SESSION_EVENTS.jsonl"
LANE_STATE_FILE = "OBSERVATION_STATE.json"
LANE_LEDGER_FILE = "OBSERVATION_LEDGER.csv"
LANE_SUMMARY_FILE = "OBSERVATION_SUMMARY.json"
LANE_EVENTS_FILE = "OBSERVATION_EVENTS.jsonl"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.+-]{1,128}$")

SAFETY = {
    "paper_only": True,
    "observation_only": True,
    "deterministic_fan_out": True,
    "canonical_runtime_connected": False,
    "canonical_selection_allowed": False,
    "canonical_activation_allowed": False,
    "human_cutover_gate_creation_allowed": False,
    "runtime_control_allowed": False,
    "canonical_state_write_allowed": False,
    "canonical_ledger_write_allowed": False,
    "package_source_import_allowed": False,
    "implementation_registration_allowed": False,
    "real_orders_allowed": False,
    "broker_execution_allowed": False,
    "auto_trading_allowed": False,
    "real_money_allowed": False,
    "option_selling_allowed": False,
    "profitability_claim_allowed": False,
}

_LEDGER_FIELDS = (
    "sequence",
    "cycle_id",
    "event_time",
    "input_identity",
    "event_type",
    "strategy_id",
    "strategy_version",
    "parameters_hash",
    "signal",
    "option_side",
    "entry_price",
    "mark_price",
    "exit_price",
    "quantity",
    "realized_pnl",
    "unrealized_pnl",
    "position_status",
    "reason",
)


class ParallelObservationError(RuntimeError):
    """Raised when an isolated observation safety invariant fails."""


class ObservationSessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class ObservationPositionStatus(str, Enum):
    FLAT = "FLAT"
    OPEN = "OPEN"


def _now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def _safe_float(value: Any, *, field: str, allow_none: bool = True) -> float | None:
    if value is None and allow_none:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ParallelObservationError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ParallelObservationError(f"{field} must be finite")
    return number


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _signed_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("payload_hash", None)
    clean["payload_hash"] = canonical_mapping_hash(clean)
    return clean


def _write_signed_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    signed = _signed_payload(payload)
    _atomic_write_text(
        path,
        json.dumps(signed, indent=2, sort_keys=True) + "\n",
    )
    return signed


def _read_signed_json(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ParallelObservationError(f"{label} is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParallelObservationError(f"{label} is unreadable") from exc
    if not isinstance(payload, dict):
        raise ParallelObservationError(f"{label} must be a JSON object")
    supplied = str(payload.get("payload_hash", ""))
    expected = canonical_mapping_hash(
        {key: value for key, value in payload.items() if key != "payload_hash"}
    )
    if not supplied or supplied != expected:
        raise ParallelObservationError(f"{label} hash verification failed")
    return payload


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def observation_root(workspace: str | Path) -> Path:
    return Path(workspace).resolve() / OBSERVATION_FOLDER


def _sessions_root(workspace: str | Path) -> Path:
    return observation_root(workspace) / "sessions"


def _session_root(workspace: str | Path, session_id: str) -> Path:
    if not _SAFE_ID.fullmatch(str(session_id)):
        raise ParallelObservationError("invalid observation session_id")
    return _sessions_root(workspace) / str(session_id)


def _lane_directory(session_root: Path, lane_id: str) -> Path:
    if not _SAFE_ID.fullmatch(str(lane_id)):
        raise ParallelObservationError("invalid observation lane_id")
    return session_root / "lanes" / str(lane_id)


def _read_jsonl_verified(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    previous = ""
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ParallelObservationError(
                f"{label} line {line_number} is invalid JSON"
            ) from exc
        if not isinstance(record, dict):
            raise ParallelObservationError(
                f"{label} line {line_number} must be an object"
            )
        supplied = str(record.get("event_hash", ""))
        clean = {key: value for key, value in record.items() if key != "event_hash"}
        expected = canonical_mapping_hash(clean)
        if not supplied or supplied != expected:
            raise ParallelObservationError(
                f"{label} line {line_number} hash verification failed"
            )
        if str(record.get("previous_event_hash", "")) != previous:
            raise ParallelObservationError(
                f"{label} line {line_number} chain verification failed"
            )
        expected_sequence = len(records) + 1
        if int(record.get("sequence", 0)) != expected_sequence:
            raise ParallelObservationError(
                f"{label} sequence verification failed"
            )
        previous = supplied
        records.append(record)
    return records


def _append_event(
    path: Path,
    *,
    event_type: str,
    event_time: str,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    records = _read_jsonl_verified(path, label=path.name)
    clean = {
        "schema_version": PARALLEL_OBSERVATION_SCHEMA_VERSION,
        "sequence": len(records) + 1,
        "event_type": str(event_type),
        "event_time": str(event_time),
        "previous_event_hash": (
            str(records[-1]["event_hash"]) if records else ""
        ),
        "details": dict(details),
        **SAFETY,
    }
    record = {**clean, "event_hash": canonical_mapping_hash(clean)}
    line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    return record


def _read_ledger(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != _LEDGER_FIELDS:
                raise ParallelObservationError("observation ledger header mismatch")
            return [dict(row) for row in reader]
    except OSError as exc:
        raise ParallelObservationError("observation ledger is unreadable") from exc


def _write_ledger(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_LEDGER_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in _LEDGER_FIELDS})
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


@dataclass(frozen=True)
class ObservationLaneConfig:
    strategy_id: str
    strategy_version: str
    parameters: Mapping[str, Any]
    quantity: float = 1.0

    def __post_init__(self) -> None:
        strategy_id = str(self.strategy_id).strip()
        strategy_version = str(self.strategy_version).strip()
        if not strategy_id or not strategy_version:
            raise ParallelObservationError(
                "strategy_id and strategy_version are required"
            )
        quantity = _safe_float(self.quantity, field="quantity", allow_none=False)
        if quantity is None or quantity <= 0:
            raise ParallelObservationError("quantity must be greater than zero")
        object.__setattr__(self, "strategy_id", strategy_id)
        object.__setattr__(self, "strategy_version", strategy_version)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "parameters", _freeze(self.parameters))

    @property
    def parameters_hash(self) -> str:
        return canonical_mapping_hash(self.parameters)

    @property
    def lane_id(self) -> str:
        raw = (
            f"{self.strategy_id}.{self.strategy_version}."
            f"{self.parameters_hash[:16]}"
        )
        safe = re.sub(r"[^A-Za-z0-9_.+-]", "_", raw)
        if not _SAFE_ID.fullmatch(safe):
            raise ParallelObservationError("derived lane_id is invalid")
        return safe

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "parameters": dict(self.parameters),
            "parameters_hash": self.parameters_hash,
            "quantity": self.quantity,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ObservationLaneConfig":
        return cls(
            strategy_id=str(payload.get("strategy_id", "")),
            strategy_version=str(
                payload.get("strategy_version") or payload.get("version") or ""
            ),
            parameters=(
                dict(payload.get("parameters", {}))
                if isinstance(payload.get("parameters", {}), Mapping)
                else {}
            ),
            quantity=float(payload.get("quantity", 1.0)),
        )


def eligible_parallel_observation_strategies(
    registry: StrategyRegistry,
) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for registration in registry.list_registrations():
        manifest = registration.manifest
        default_parameters = manifest.validate_parameters(None)
        compatible = False
        reason = "implementation is metadata-only"
        if registration.status is RegistrationStatus.EXECUTABLE_REVIEWED:
            try:
                implementation = registry.create(
                    manifest.strategy_id,
                    manifest.strategy_version,
                    parameters=default_parameters,
                )
                compatible = isinstance(
                    implementation,
                    ForwardPaperCompatibilityAdapter,
                )
                reason = (
                    "reviewed forward-compatible adapter"
                    if compatible
                    else "reviewed implementation lacks recorded-paper adapter"
                )
            except Exception as exc:  # fail-closed UI evidence
                reason = f"compatibility check failed: {exc}"
        records.append(
            {
                "strategy_id": manifest.strategy_id,
                "strategy_version": manifest.strategy_version,
                "display_name": manifest.display_name,
                "implementation_key": manifest.implementation_key,
                "registration_status": registration.status.value,
                "eligible": compatible,
                "reason": reason,
                "default_parameters": dict(default_parameters),
                "required_timeframe": manifest.required_timeframe,
                "source": registration.source,
            }
        )
    return tuple(
        sorted(
            records,
            key=lambda item: (
                not bool(item["eligible"]),
                str(item["display_name"]).lower(),
                str(item["strategy_version"]),
            ),
        )
    )


def _validate_lanes(
    registry: StrategyRegistry,
    lane_configs: Iterable[ObservationLaneConfig | Mapping[str, Any]],
    *,
    timeframe: str,
) -> tuple[ObservationLaneConfig, ...]:
    normalized = tuple(
        item if isinstance(item, ObservationLaneConfig) else ObservationLaneConfig.from_mapping(item)
        for item in lane_configs
    )
    if len(normalized) < 2:
        raise ParallelObservationError(
            "parallel observation requires at least two isolated lanes"
        )
    lane_ids = [item.lane_id for item in normalized]
    if len(lane_ids) != len(set(lane_ids)):
        raise ParallelObservationError("duplicate observation lane identity")

    reviewed: list[ObservationLaneConfig] = []
    for lane in normalized:
        registration = registry.get(lane.strategy_id, lane.strategy_version)
        if registration.status is not RegistrationStatus.EXECUTABLE_REVIEWED:
            raise ParallelObservationError(
                f"lane {lane.lane_id} implementation is not reviewed"
            )
        if registration.manifest.required_timeframe != timeframe:
            raise ParallelObservationError(
                f"lane {lane.lane_id} requires timeframe "
                f"{registration.manifest.required_timeframe}"
            )
        normalized_parameters = registration.manifest.validate_parameters(
            lane.parameters
        )
        normalized_lane = ObservationLaneConfig(
            strategy_id=lane.strategy_id,
            strategy_version=lane.strategy_version,
            parameters=normalized_parameters,
            quantity=lane.quantity,
        )
        implementation = registry.create(
            normalized_lane.strategy_id,
            normalized_lane.strategy_version,
            parameters=normalized_lane.parameters,
        )
        if not isinstance(implementation, ForwardPaperCompatibilityAdapter):
            raise ParallelObservationError(
                f"lane {normalized_lane.lane_id} lacks forward-paper compatibility"
            )
        reviewed.append(normalized_lane)
    normalized_ids = [item.lane_id for item in reviewed]
    if len(normalized_ids) != len(set(normalized_ids)):
        raise ParallelObservationError(
            "duplicate observation lane identity after parameter normalization"
        )
    return tuple(sorted(reviewed, key=lambda item: item.lane_id))


def _initial_lane_state(
    *,
    session_id: str,
    lane: ObservationLaneConfig,
    event_time: str,
) -> dict[str, Any]:
    return {
        "schema_version": PARALLEL_OBSERVATION_SCHEMA_VERSION,
        "session_id": session_id,
        **lane.to_dict(),
        "session_status": ObservationSessionStatus.ACTIVE.value,
        "position_status": ObservationPositionStatus.FLAT.value,
        "position": None,
        "cycle_count": 0,
        "open_count": 0,
        "close_count": 0,
        "realized_pnl": 0.0,
        "last_unrealized_pnl": 0.0,
        "last_cycle_id": "",
        "last_input_identity": "",
        "last_event_type": "SESSION_CREATED",
        "updated_at": event_time,
        **SAFETY,
    }


def create_parallel_observation_session(
    workspace: str | Path,
    registry: StrategyRegistry,
    lane_configs: Iterable[ObservationLaneConfig | Mapping[str, Any]],
    *,
    session_id: str,
    created_by: str,
    symbol: str,
    timeframe: str,
    event_time: str | None = None,
) -> dict[str, Any]:
    actor = str(created_by).strip()
    symbol_text = str(symbol).strip()
    timeframe_text = str(timeframe).strip()
    if not actor or not symbol_text or not timeframe_text:
        raise ParallelObservationError(
            "created_by, symbol and timeframe are required"
        )
    root = _session_root(workspace, session_id)
    if root.exists():
        raise ParallelObservationError("observation session already exists")
    lanes = _validate_lanes(registry, lane_configs, timeframe=timeframe_text)
    now = str(event_time or _now_text())

    manifest_payload = {
        "schema_version": PARALLEL_OBSERVATION_SCHEMA_VERSION,
        "session_id": str(session_id),
        "status": ObservationSessionStatus.ACTIVE.value,
        "created_by": actor,
        "created_at": now,
        "closed_at": "",
        "symbol": symbol_text,
        "timeframe": timeframe_text,
        "lane_count": len(lanes),
        "unique_strategy_count": len({lane.strategy_id for lane in lanes}),
        "lanes": [lane.to_dict() for lane in lanes],
        "observation_root": str(root),
        **SAFETY,
    }

    try:
        root.mkdir(parents=True, exist_ok=False)
        _write_signed_json(root / SESSION_MANIFEST_FILE, manifest_payload)
        _append_event(
            root / SESSION_EVENTS_FILE,
            event_type="SESSION_CREATED",
            event_time=now,
            details={
                "session_id": str(session_id),
                "lane_ids": [lane.lane_id for lane in lanes],
                "symbol": symbol_text,
                "timeframe": timeframe_text,
            },
        )
        for lane in lanes:
            lane_root = _lane_directory(root, lane.lane_id)
            lane_root.mkdir(parents=True, exist_ok=False)
            state = _write_signed_json(
                lane_root / LANE_STATE_FILE,
                _initial_lane_state(
                    session_id=str(session_id),
                    lane=lane,
                    event_time=now,
                ),
            )
            _write_ledger(lane_root / LANE_LEDGER_FILE, [])
            _append_event(
                lane_root / LANE_EVENTS_FILE,
                event_type="LANE_CREATED",
                event_time=now,
                details={
                    "session_id": str(session_id),
                    "lane_id": lane.lane_id,
                    "strategy_id": lane.strategy_id,
                    "strategy_version": lane.strategy_version,
                    "parameters_hash": lane.parameters_hash,
                },
            )
            _write_lane_summary(lane_root, state)
        _write_session_summary(root)
    except Exception:
        # A brand-new session can be removed safely if creation did not finish.
        if root.exists():
            import shutil

            shutil.rmtree(root, ignore_errors=True)
        raise

    return parallel_observation_snapshot(workspace, session_id=str(session_id))


def _lane_config_from_manifest(payload: Mapping[str, Any]) -> ObservationLaneConfig:
    return ObservationLaneConfig.from_mapping(payload)


def _position_mark(decision: Any) -> float | None:
    for value in (decision.latest_price, decision.entry):
        if value is not None:
            return _safe_float(value, field="mark_price")
    return None


def _apply_decision(
    state: Mapping[str, Any],
    *,
    decision: Any,
    cycle_id: str,
    event_time: str,
    input_identity: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    next_state = dict(state)
    next_state.pop("payload_hash", None)
    quantity = float(next_state["quantity"])
    realized_total = float(next_state.get("realized_pnl", 0.0))
    mark = _position_mark(decision)
    current_position = next_state.get("position")
    event_type = "NO_TRADE"
    reason = str(decision.reason_text or "")
    realized_cycle = 0.0
    unrealized = 0.0
    entry_price = ""
    exit_price = ""

    if isinstance(current_position, Mapping):
        entry = float(current_position["entry_price"])
        entry_price = entry
        side = str(current_position["option_side"])
        stop = _safe_float(current_position.get("stop_loss"), field="stop_loss")
        target = _safe_float(current_position.get("target"), field="target")
        close_reason = ""
        if mark is not None and stop is not None and mark <= stop:
            close_reason = "STOP_LOSS"
        elif mark is not None and target is not None and mark >= target:
            close_reason = "TARGET"
        elif (
            bool(decision.entry_eligible)
            and str(decision.option_side) not in {"", "NO_TRADE", side}
        ):
            close_reason = "OPPOSITE_SIGNAL"

        if close_reason and mark is not None:
            exit_price = mark
            realized_cycle = round((mark - entry) * quantity, 8)
            realized_total = round(realized_total + realized_cycle, 8)
            next_state["position"] = None
            next_state["position_status"] = ObservationPositionStatus.FLAT.value
            next_state["close_count"] = int(next_state.get("close_count", 0)) + 1
            event_type = "POSITION_CLOSED"
            reason = close_reason
        else:
            if mark is not None:
                unrealized = round((mark - entry) * quantity, 8)
            next_state["position_status"] = ObservationPositionStatus.OPEN.value
            event_type = "POSITION_HELD"
    elif (
        bool(decision.entry_eligible)
        and str(decision.option_side) not in {"", "NO_TRADE"}
    ):
        entry = _safe_float(decision.entry, field="entry_price")
        if entry is None:
            entry = mark
        if entry is not None and entry > 0:
            entry_price = entry
            stop = _safe_float(decision.stop_loss, field="stop_loss")
            target = _safe_float(decision.target, field="target")
            next_state["position"] = {
                "option_side": str(decision.option_side),
                "signal": str(decision.signal),
                "entry_price": entry,
                "stop_loss": stop,
                "target": target,
                "quantity": quantity,
                "opened_cycle_id": cycle_id,
                "opened_at": event_time,
            }
            next_state["position_status"] = ObservationPositionStatus.OPEN.value
            next_state["open_count"] = int(next_state.get("open_count", 0)) + 1
            event_type = "POSITION_OPENED"
        else:
            reason = "entry price unavailable"

    next_state["cycle_count"] = int(next_state.get("cycle_count", 0)) + 1
    next_state["realized_pnl"] = realized_total
    next_state["last_unrealized_pnl"] = unrealized
    next_state["last_cycle_id"] = cycle_id
    next_state["last_input_identity"] = input_identity
    next_state["last_event_type"] = event_type
    next_state["updated_at"] = event_time

    row = {
        "sequence": next_state["cycle_count"],
        "cycle_id": cycle_id,
        "event_time": event_time,
        "input_identity": input_identity,
        "event_type": event_type,
        "strategy_id": next_state["strategy_id"],
        "strategy_version": next_state["strategy_version"],
        "parameters_hash": next_state["parameters_hash"],
        "signal": str(decision.signal),
        "option_side": str(decision.option_side),
        "entry_price": entry_price,
        "mark_price": "" if mark is None else mark,
        "exit_price": exit_price,
        "quantity": quantity,
        "realized_pnl": realized_cycle,
        "unrealized_pnl": unrealized,
        "position_status": next_state["position_status"],
        "reason": reason,
    }
    return next_state, row


def _write_lane_summary(lane_root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    ledger_path = lane_root / LANE_LEDGER_FILE
    events_path = lane_root / LANE_EVENTS_FILE
    rows = _read_ledger(ledger_path)
    events = _read_jsonl_verified(events_path, label=LANE_EVENTS_FILE)
    position = state.get("position") if isinstance(state.get("position"), Mapping) else None
    payload = {
        "schema_version": PARALLEL_OBSERVATION_SCHEMA_VERSION,
        "session_id": state["session_id"],
        "lane_id": state["lane_id"],
        "strategy_id": state["strategy_id"],
        "strategy_version": state["strategy_version"],
        "parameters_hash": state["parameters_hash"],
        "session_status": state["session_status"],
        "position_status": state["position_status"],
        "position": dict(position) if position else None,
        "cycle_count": int(state["cycle_count"]),
        "open_count": int(state["open_count"]),
        "close_count": int(state["close_count"]),
        "realized_pnl": float(state["realized_pnl"]),
        "unrealized_pnl": float(state["last_unrealized_pnl"]),
        "last_cycle_id": state["last_cycle_id"],
        "last_event_type": state["last_event_type"],
        "state_path": str(lane_root / LANE_STATE_FILE),
        "ledger_path": str(ledger_path),
        "events_path": str(events_path),
        "ledger_row_count": len(rows),
        "event_count": len(events),
        "ledger_sha256": _file_sha256(ledger_path),
        "last_event_hash": str(events[-1]["event_hash"]) if events else "",
        "comparison_only": True,
        "profitability_claim": False,
        **SAFETY,
    }
    return _write_signed_json(lane_root / LANE_SUMMARY_FILE, payload)


def _write_session_summary(session_root: Path) -> dict[str, Any]:
    manifest = _read_signed_json(
        session_root / SESSION_MANIFEST_FILE,
        label="session manifest",
    )
    lane_summaries: list[dict[str, Any]] = []
    for lane_payload in manifest["lanes"]:
        lane_root = _lane_directory(session_root, str(lane_payload["lane_id"]))
        state = _read_signed_json(
            lane_root / LANE_STATE_FILE,
            label="lane state",
        )
        lane_summaries.append(_write_lane_summary(lane_root, state))
    events = _read_jsonl_verified(
        session_root / SESSION_EVENTS_FILE,
        label=SESSION_EVENTS_FILE,
    )
    cycle_events = [event for event in events if event["event_type"] == "CYCLE_COMPLETED"]
    payload = {
        "schema_version": PARALLEL_OBSERVATION_SCHEMA_VERSION,
        "session_id": manifest["session_id"],
        "status": manifest["status"],
        "symbol": manifest["symbol"],
        "timeframe": manifest["timeframe"],
        "lane_count": len(lane_summaries),
        "unique_strategy_count": manifest["unique_strategy_count"],
        "cycle_count": len(cycle_events),
        "active_position_count": sum(
            lane["position_status"] == ObservationPositionStatus.OPEN.value
            for lane in lane_summaries
        ),
        "aggregate_realized_pnl": round(
            sum(float(lane["realized_pnl"]) for lane in lane_summaries),
            8,
        ),
        "aggregate_unrealized_pnl": round(
            sum(float(lane["unrealized_pnl"]) for lane in lane_summaries),
            8,
        ),
        "lanes": lane_summaries,
        "session_events_path": str(session_root / SESSION_EVENTS_FILE),
        "session_event_count": len(events),
        "last_session_event_hash": str(events[-1]["event_hash"]) if events else "",
        "comparison_only": True,
        "ranking_or_winner_claim": False,
        "profitability_claim": False,
        **SAFETY,
    }
    return _write_signed_json(session_root / SESSION_SUMMARY_FILE, payload)


def _load_manifest(workspace: str | Path, session_id: str) -> tuple[Path, dict[str, Any]]:
    root = _session_root(workspace, session_id)
    manifest = _read_signed_json(root / SESSION_MANIFEST_FILE, label="session manifest")
    if manifest.get("schema_version") != PARALLEL_OBSERVATION_SCHEMA_VERSION:
        raise ParallelObservationError("unsupported observation schema version")
    if manifest.get("session_id") != session_id:
        raise ParallelObservationError("session identity mismatch")
    forbidden = (
        manifest.get("canonical_runtime_connected"),
        manifest.get("canonical_selection_allowed"),
        manifest.get("canonical_activation_allowed"),
        manifest.get("real_orders_allowed"),
        manifest.get("broker_execution_allowed"),
        manifest.get("real_money_allowed"),
    )
    if any(bool(value) for value in forbidden):
        raise ParallelObservationError("session manifest contains forbidden authority")
    return root, manifest


def run_parallel_observation_cycle(
    workspace: str | Path,
    registry: StrategyRegistry,
    *,
    session_id: str,
    cycle_id: str,
    request: RecordedStrategyInput,
    event_time: str | None = None,
) -> dict[str, Any]:
    cycle = str(cycle_id).strip()
    if not _SAFE_ID.fullmatch(cycle):
        raise ParallelObservationError("invalid observation cycle_id")
    root, manifest = _load_manifest(workspace, session_id)
    if manifest["status"] != ObservationSessionStatus.ACTIVE.value:
        raise ParallelObservationError("observation session is not active")
    if request.symbol != manifest["symbol"]:
        raise ParallelObservationError("recorded input symbol mismatch")
    if request.timeframe != manifest["timeframe"]:
        raise ParallelObservationError("recorded input timeframe mismatch")

    session_events = _read_jsonl_verified(
        root / SESSION_EVENTS_FILE,
        label=SESSION_EVENTS_FILE,
    )
    if any(
        event["event_type"] == "CYCLE_COMPLETED"
        and str(event.get("details", {}).get("cycle_id", "")) == cycle
        for event in session_events
    ):
        raise ParallelObservationError("duplicate observation cycle_id")

    now = str(event_time or _now_text())
    prepared: list[tuple[Path, dict[str, Any], dict[str, Any], Any]] = []
    lane_configs = tuple(
        _lane_config_from_manifest(item)
        for item in manifest["lanes"]
    )
    _validate_lanes(registry, lane_configs, timeframe=manifest["timeframe"])

    # Evaluate every lane before writing any cycle evidence.  A failing lane
    # therefore cannot leave another lane one cycle ahead.
    for lane in lane_configs:
        lane_root = _lane_directory(root, lane.lane_id)
        state = _read_signed_json(
            lane_root / LANE_STATE_FILE,
            label=f"lane state {lane.lane_id}",
        )
        if state["session_status"] != ObservationSessionStatus.ACTIVE.value:
            raise ParallelObservationError("lane is not active")
        if state.get("last_cycle_id") == cycle:
            raise ParallelObservationError("lane already contains cycle_id")
        _read_jsonl_verified(lane_root / LANE_EVENTS_FILE, label=LANE_EVENTS_FILE)
        _read_ledger(lane_root / LANE_LEDGER_FILE)
        evaluator = RegisteredRecordedEvaluator(
            registry=registry,
            strategy_id=lane.strategy_id,
            strategy_version=lane.strategy_version,
            parameters=lane.parameters,
        )
        result = evaluator.evaluate(
            request,
            execution_mode=ExecutionMode.FORWARD_PAPER,
        )
        next_state, row = _apply_decision(
            state,
            decision=result.decision,
            cycle_id=cycle,
            event_time=now,
            input_identity=request.input_identity,
        )
        prepared.append((lane_root, next_state, row, result))

    lane_event_hashes: dict[str, str] = {}
    for lane_root, next_state, row, result in prepared:
        ledger_path = lane_root / LANE_LEDGER_FILE
        rows = _read_ledger(ledger_path)
        rows.append(row)
        _write_ledger(ledger_path, rows)
        signed_state = _write_signed_json(lane_root / LANE_STATE_FILE, next_state)
        event = _append_event(
            lane_root / LANE_EVENTS_FILE,
            event_type=str(row["event_type"]),
            event_time=now,
            details={
                "session_id": session_id,
                "lane_id": next_state["lane_id"],
                "cycle_id": cycle,
                "input_identity": request.input_identity,
                "decision": result.decision.to_dict(),
                "metadata": result.metadata.to_dict(),
                "ledger_row": dict(row),
                "state_hash": signed_state["payload_hash"],
            },
        )
        lane_event_hashes[str(next_state["lane_id"])] = str(event["event_hash"])
        _write_lane_summary(lane_root, signed_state)

    _append_event(
        root / SESSION_EVENTS_FILE,
        event_type="CYCLE_COMPLETED",
        event_time=now,
        details={
            "session_id": session_id,
            "cycle_id": cycle,
            "input_identity": request.input_identity,
            "lane_event_hashes": lane_event_hashes,
            "lane_count": len(prepared),
        },
    )
    _write_session_summary(root)
    return parallel_observation_snapshot(workspace, session_id=session_id)


def close_parallel_observation_session(
    workspace: str | Path,
    *,
    session_id: str,
    closed_by: str,
    event_time: str | None = None,
) -> dict[str, Any]:
    actor = str(closed_by).strip()
    if not actor:
        raise ParallelObservationError("closed_by is required")
    root, manifest = _load_manifest(workspace, session_id)
    if manifest["status"] != ObservationSessionStatus.ACTIVE.value:
        raise ParallelObservationError("observation session is not active")

    states: list[tuple[Path, dict[str, Any]]] = []
    for lane_payload in manifest["lanes"]:
        lane_root = _lane_directory(root, str(lane_payload["lane_id"]))
        state = _read_signed_json(lane_root / LANE_STATE_FILE, label="lane state")
        if state["position_status"] != ObservationPositionStatus.FLAT.value:
            raise ParallelObservationError(
                "cannot close observation session while a lane is OPEN"
            )
        states.append((lane_root, state))

    now = str(event_time or _now_text())
    updated_manifest = dict(manifest)
    updated_manifest.pop("payload_hash", None)
    updated_manifest["status"] = ObservationSessionStatus.CLOSED.value
    updated_manifest["closed_at"] = now
    updated_manifest["closed_by"] = actor
    _write_signed_json(root / SESSION_MANIFEST_FILE, updated_manifest)

    for lane_root, state in states:
        updated_state = dict(state)
        updated_state.pop("payload_hash", None)
        updated_state["session_status"] = ObservationSessionStatus.CLOSED.value
        updated_state["updated_at"] = now
        signed_state = _write_signed_json(lane_root / LANE_STATE_FILE, updated_state)
        _append_event(
            lane_root / LANE_EVENTS_FILE,
            event_type="LANE_CLOSED",
            event_time=now,
            details={
                "session_id": session_id,
                "lane_id": updated_state["lane_id"],
                "closed_by": actor,
                "state_hash": signed_state["payload_hash"],
            },
        )
        _write_lane_summary(lane_root, signed_state)

    _append_event(
        root / SESSION_EVENTS_FILE,
        event_type="SESSION_CLOSED",
        event_time=now,
        details={"session_id": session_id, "closed_by": actor},
    )
    _write_session_summary(root)
    return parallel_observation_snapshot(workspace, session_id=session_id)


def _session_snapshot(session_root: Path) -> dict[str, Any]:
    manifest = _read_signed_json(
        session_root / SESSION_MANIFEST_FILE,
        label="session manifest",
    )
    summary = _read_signed_json(
        session_root / SESSION_SUMMARY_FILE,
        label="session summary",
    )
    _read_jsonl_verified(
        session_root / SESSION_EVENTS_FILE,
        label=SESSION_EVENTS_FILE,
    )
    lanes: list[dict[str, Any]] = []
    for lane_payload in manifest["lanes"]:
        lane_root = _lane_directory(session_root, str(lane_payload["lane_id"]))
        state = _read_signed_json(lane_root / LANE_STATE_FILE, label="lane state")
        lane_summary = _read_signed_json(
            lane_root / LANE_SUMMARY_FILE,
            label="lane summary",
        )
        events = _read_jsonl_verified(
            lane_root / LANE_EVENTS_FILE,
            label=LANE_EVENTS_FILE,
        )
        rows = _read_ledger(lane_root / LANE_LEDGER_FILE)
        if lane_summary["ledger_row_count"] != len(rows):
            raise ParallelObservationError("lane ledger row count mismatch")
        if lane_summary["event_count"] != len(events):
            raise ParallelObservationError("lane event count mismatch")
        if lane_summary["ledger_sha256"] != _file_sha256(
            lane_root / LANE_LEDGER_FILE
        ):
            raise ParallelObservationError("lane ledger hash mismatch")
        if lane_summary["cycle_count"] != state["cycle_count"]:
            raise ParallelObservationError("lane state/summary cycle mismatch")
        lanes.append(lane_summary)

    return {
        "schema_version": PARALLEL_OBSERVATION_SCHEMA_VERSION,
        "session_id": manifest["session_id"],
        "status": manifest["status"],
        "created_by": manifest["created_by"],
        "created_at": manifest["created_at"],
        "closed_at": manifest.get("closed_at", ""),
        "symbol": manifest["symbol"],
        "timeframe": manifest["timeframe"],
        "lane_count": len(lanes),
        "unique_strategy_count": manifest["unique_strategy_count"],
        "cycle_count": summary["cycle_count"],
        "active_position_count": summary["active_position_count"],
        "aggregate_realized_pnl": summary["aggregate_realized_pnl"],
        "aggregate_unrealized_pnl": summary["aggregate_unrealized_pnl"],
        "lanes": lanes,
        "session_root": str(session_root),
        "manifest_path": str(session_root / SESSION_MANIFEST_FILE),
        "summary_path": str(session_root / SESSION_SUMMARY_FILE),
        "events_path": str(session_root / SESSION_EVENTS_FILE),
        "snapshot_hash": canonical_mapping_hash(
            {
                "manifest_hash": manifest["payload_hash"],
                "summary_hash": summary["payload_hash"],
                "lane_summary_hashes": [lane["payload_hash"] for lane in lanes],
            }
        ),
        "comparison_only": True,
        "ranking_or_winner_claim": False,
        "profitability_claim": False,
        **SAFETY,
    }


def parallel_observation_snapshot(
    workspace: str | Path,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    sessions_root = _sessions_root(workspace)
    sessions: list[dict[str, Any]] = []
    if sessions_root.is_dir():
        for candidate in sorted(sessions_root.iterdir()):
            if candidate.is_dir() and (candidate / SESSION_MANIFEST_FILE).is_file():
                sessions.append(_session_snapshot(candidate))

    selected: dict[str, Any] | None = None
    if session_id is not None:
        selected = next(
            (item for item in sessions if item["session_id"] == session_id),
            None,
        )
        if selected is None:
            raise ParallelObservationError("observation session was not found")
    elif sessions:
        selected = sessions[-1]

    active = [item for item in sessions if item["status"] == ObservationSessionStatus.ACTIVE.value]
    payload = {
        "schema_version": PARALLEL_OBSERVATION_SCHEMA_VERSION,
        "status": "PASS",
        "session_count": len(sessions),
        "active_session_count": len(active),
        "sessions": sessions,
        "selected_session": selected or {},
        "latest_session_id": selected["session_id"] if selected else "",
        "observation_root": str(observation_root(workspace)),
        "operator_message": (
            "No parallel observation session exists."
            if not sessions
            else (
                f"Parallel observation sessions: {len(sessions)}; "
                f"active: {len(active)}; latest: {selected['session_id']}"
            )
        ),
        **SAFETY,
    }
    payload["snapshot_hash"] = canonical_mapping_hash(payload)
    return payload


def load_recorded_input_from_csv(
    index_csv: str | Path,
    premium_csv: str | Path,
    *,
    er20: float | None,
    symbol: str,
    timeframe: str,
    data_start: str | None = None,
    data_end: str | None = None,
) -> RecordedStrategyInput:
    def read_rows(path_value: str | Path, label: str) -> list[dict[str, str]]:
        path = Path(path_value)
        if not path.is_file():
            raise ParallelObservationError(f"{label} CSV is missing: {path}")
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    raise ParallelObservationError(f"{label} CSV has no header")
                rows = [dict(row) for row in reader]
        except OSError as exc:
            raise ParallelObservationError(f"{label} CSV is unreadable") from exc
        if not rows:
            raise ParallelObservationError(f"{label} CSV is empty")
        return rows

    return RecordedStrategyInput(
        index_rows=read_rows(index_csv, "index"),
        premium_rows=read_rows(premium_csv, "premium"),
        er20=er20,
        symbol=symbol,
        timeframe=timeframe,
        data_start=data_start,
        data_end=data_end,
    )


def guard_payload() -> dict[str, Any]:
    return {
        "schema_version": PARALLEL_OBSERVATION_SCHEMA_VERSION,
        "guard_check_status": "PASS",
        "minimum_lane_count": 2,
        "reviewed_forward_compatible_only": True,
        "metadata_only_strategy_blocked": True,
        "per_lane_state_isolation": True,
        "per_lane_ledger_isolation": True,
        "per_lane_pnl_isolation": True,
        "tamper_evident_state_and_event_chains": True,
        "restart_resume_supported": True,
        "open_lane_session_close_blocked": True,
        "same_input_deterministic_fan_out": True,
        "comparison_without_ranking_claim": True,
        **SAFETY,
    }
