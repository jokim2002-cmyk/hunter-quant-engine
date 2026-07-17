"""Safe product-facing strategy manager model for HQE Phase 5.

The manager combines the existing strategy-pack registry, paper-selection
configuration and Phase 4 canonical runtime truth into one deterministic UI
snapshot.  It can authorize only configuration selection/clearing; it cannot
create a human cutover gate, start a runtime, write lifecycle evidence, place
orders or enable real money.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.errors import ProductUiModelError
from src.multi_strategy.execution import canonical_mapping_hash

PRODUCT_STRATEGY_MANAGER_SCHEMA_VERSION = "1.0.0"

SAFETY = {
    "paper_only": True,
    "configuration_selection_only": True,
    "canonical_activation_allowed": False,
    "human_gate_creation_allowed": False,
    "runtime_control_allowed": False,
    "lifecycle_write_allowed": False,
    "real_orders_allowed": False,
    "broker_execution_allowed": False,
    "auto_trading_allowed": False,
    "real_money_allowed": False,
    "option_selling_allowed": False,
    "parallel_isolated_observation_allowed": True,
}


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def _text(value: Any) -> str:
    return str(value or "").strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return value
    return ()


def _parameters_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    for key in (
        "parameters",
        "default_parameters",
        "parameter_defaults",
        "params",
    ):
        candidate = payload.get(key)
        if isinstance(candidate, Mapping):
            return dict(candidate)
    rules = payload.get("rules")
    if isinstance(rules, Mapping):
        return dict(rules)
    return {}


@dataclass(frozen=True)
class ProductStrategyRecord:
    strategy_id: str
    name: str
    version: str
    source: str
    path: str
    category: str
    status: str
    valid: bool
    paper_only: bool
    reviewed_current_smc: bool
    parameters: Mapping[str, Any]
    validation: Mapping[str, Any]
    safety: Mapping[str, Any]
    description: str = ""

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ProductUiModelError("strategy_id is required")
        if not self.name:
            raise ProductUiModelError("strategy name is required")
        if not self.version:
            raise ProductUiModelError("strategy version is required")
        object.__setattr__(self, "parameters", _freeze(self.parameters))
        object.__setattr__(self, "validation", _freeze(self.validation))
        object.__setattr__(self, "safety", _freeze(self.safety))

    @property
    def identity(self) -> str:
        return f"{self.strategy_id}@{self.version}"

    @property
    def record_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "path": self.path,
            "category": self.category,
            "status": self.status,
            "valid": self.valid,
            "paper_only": self.paper_only,
            "reviewed_current_smc": self.reviewed_current_smc,
            "parameters": dict(self.parameters),
            "validation": dict(self.validation),
            "safety": dict(self.safety),
            "description": self.description,
            "identity": self.identity,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class StrategyChangeDecision:
    allowed: bool
    action: str
    strategy_id: str
    strategy_version: str
    blockers: tuple[str, ...]
    warning: str
    configuration_only: bool = True
    canonical_activation_allowed: bool = False
    human_gate_creation_allowed: bool = False
    runtime_control_allowed: bool = False
    real_orders_allowed: bool = False
    broker_execution_allowed: bool = False
    real_money_allowed: bool = False

    @property
    def decision_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "allowed": self.allowed,
            "action": self.action,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "blockers": list(self.blockers),
            "warning": self.warning,
            "configuration_only": self.configuration_only,
            "canonical_activation_allowed": self.canonical_activation_allowed,
            "human_gate_creation_allowed": self.human_gate_creation_allowed,
            "runtime_control_allowed": self.runtime_control_allowed,
            "real_orders_allowed": self.real_orders_allowed,
            "broker_execution_allowed": self.broker_execution_allowed,
            "real_money_allowed": self.real_money_allowed,
        }
        if include_hash:
            payload["decision_hash"] = self.decision_hash
        return payload


def normalize_strategy_records(
    pack_snapshot: Mapping[str, Any],
    builder_snapshot: Mapping[str, Any],
) -> tuple[ProductStrategyRecord, ...]:
    raw_records = _sequence(pack_snapshot.get("packs"))
    if not raw_records:
        registry = _mapping(builder_snapshot.get("registry"))
        raw_records = _sequence(registry.get("packs"))

    records: list[ProductStrategyRecord] = []
    identities: set[tuple[str, str]] = set()
    for index, raw in enumerate(raw_records):
        record = _mapping(raw)
        payload = _mapping(record.get("payload"))
        strategy_id = _text(
            record.get("strategy_id")
            or payload.get("strategy_id")
            or payload.get("id")
        )
        version = _text(
            record.get("version")
            or payload.get("strategy_version")
            or payload.get("version")
        )
        name = _text(
            record.get("name")
            or payload.get("display_name")
            or payload.get("name")
            or strategy_id
        )
        if not strategy_id or not version:
            continue
        identity = (strategy_id, version)
        if identity in identities:
            raise ProductUiModelError(
                f"duplicate strategy record: {strategy_id}@{version}"
            )
        identities.add(identity)

        safety = dict(_mapping(payload.get("safety")))
        validation = dict(_mapping(payload.get("validation")))
        paper_only = bool(
            safety.get("paper_only", record.get("paper_only", True))
        )
        records.append(
            ProductStrategyRecord(
                strategy_id=strategy_id,
                name=name,
                version=version,
                source=_text(record.get("source") or "unknown"),
                path=_text(record.get("path")),
                category=_text(
                    record.get("category") or payload.get("category")
                ),
                status=_text(record.get("status") or "UNKNOWN"),
                valid=bool(record.get("valid", False)),
                paper_only=paper_only,
                reviewed_current_smc=(
                    strategy_id == CURRENT_SMC_STRATEGY_ID
                    and version == CURRENT_SMC_STRATEGY_VERSION
                ),
                parameters=_parameters_from_payload(payload),
                validation=validation,
                safety=safety,
                description=_text(payload.get("description")),
            )
        )

    return tuple(
        sorted(
            records,
            key=lambda item: (
                not item.reviewed_current_smc,
                item.name.lower(),
                item.version,
            ),
        )
    )


def _selected_configuration(
    builder_snapshot: Mapping[str, Any],
    records: Sequence[ProductStrategyRecord],
) -> dict[str, Any]:
    selection = dict(_mapping(builder_snapshot.get("selection")))
    strategy_id = _text(
        selection.get("strategy_id")
        or selection.get("selected_strategy_id")
    )
    version = _text(
        selection.get("version")
        or selection.get("strategy_version")
        or selection.get("selected_strategy_version")
    )
    selected_path = _text(
        selection.get("path")
        or selection.get("selected_path")
        or selection.get("pack_path")
    )

    if not strategy_id and selected_path:
        for record in records:
            if record.path and Path(record.path) == Path(selected_path):
                strategy_id = record.strategy_id
                version = record.version
                break

    display_text = _text(selection.get("display_text"))
    return {
        "configured": bool(strategy_id or selected_path),
        "strategy_id": strategy_id,
        "strategy_version": version,
        "path": selected_path,
        "display_text": display_text or "No paper strategy configured",
        "raw": selection,
    }


def _lifecycle(
    runtime_snapshot: Mapping[str, Any],
    paper_snapshot: Mapping[str, Any],
) -> str:
    value = _text(runtime_snapshot.get("multi_strategy_lifecycle"))
    if not value:
        position = _mapping(paper_snapshot.get("position"))
        value = _text(
            position.get("status")
            or paper_snapshot.get("position_status")
            or paper_snapshot.get("status")
        )
    value = value.upper() or "FLAT"
    return value if value in {"FLAT", "OPEN", "HELD", "CLOSED"} else "FLAT"


def build_product_strategy_manager_snapshot(
    *,
    pack_snapshot: Mapping[str, Any],
    builder_snapshot: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    paper_snapshot: Mapping[str, Any],
    runtime_running: bool,
    observation_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    records = normalize_strategy_records(pack_snapshot, builder_snapshot)
    selected = _selected_configuration(builder_snapshot, records)
    lifecycle = _lifecycle(runtime_snapshot, paper_snapshot)
    global_blockers: list[str] = []
    if runtime_running:
        global_blockers.append("Paper runtime is running")
    if lifecycle in {"OPEN", "HELD"}:
        global_blockers.append(
            f"Paper position lifecycle is {lifecycle}"
        )

    canonical_strategy_id = _text(runtime_snapshot.get("strategy_id"))
    canonical_strategy_version = _text(
        runtime_snapshot.get("strategy_version")
    )
    runtime_mode = _text(
        runtime_snapshot.get("multi_strategy_runtime_mode")
    ) or "LEGACY_COMPATIBILITY"
    gate_status = _text(
        runtime_snapshot.get("multi_strategy_gate_status")
    ) or "MISSING"
    observation = dict(_mapping(observation_snapshot or {}))
    selected_observation = dict(
        _mapping(observation.get("selected_session"))
    )

    payload = {
        "schema_version": PRODUCT_STRATEGY_MANAGER_SCHEMA_VERSION,
        "status": "PASS",
        "available_count": len(records),
        "valid_count": sum(record.valid for record in records),
        "records": [record.to_dict() for record in records],
        "selected_configuration": selected,
        "canonical_runtime": {
            "strategy_id": canonical_strategy_id,
            "strategy_version": canonical_strategy_version,
            "runtime_mode": runtime_mode,
            "gate_status": gate_status,
            "lifecycle": lifecycle,
            "runtime_running": bool(runtime_running),
            "namespace": _text(
                runtime_snapshot.get("multi_strategy_namespace")
            ),
        },
        "parallel_observation": {
            "status": _text(observation.get("status")) or "PASS",
            "session_count": int(observation.get("session_count", 0) or 0),
            "active_session_count": int(
                observation.get("active_session_count", 0) or 0
            ),
            "latest_session_id": _text(
                observation.get("latest_session_id")
            ),
            "latest_session_status": _text(
                selected_observation.get("status")
            ),
            "latest_cycle_count": int(
                selected_observation.get("cycle_count", 0) or 0
            ),
            "latest_lane_count": int(
                selected_observation.get("lane_count", 0) or 0
            ),
            "active_position_count": int(
                selected_observation.get("active_position_count", 0) or 0
            ),
            "observation_root": _text(
                observation.get("observation_root")
            ),
            "operator_message": _text(
                observation.get("operator_message")
            ) or "No parallel observation session exists.",
            "canonical_runtime_connected": False,
            "canonical_selection_allowed": False,
            "canonical_activation_allowed": False,
            "real_orders_allowed": False,
        },
        "selection_change_allowed": not global_blockers,
        "clear_selection_allowed": not global_blockers,
        "global_blockers": global_blockers,
        "operator_message": (
            "Strategy configuration can be changed safely. "
            "Canonical activation remains separately human-gated."
            if not global_blockers
            else "Strategy change blocked: " + "; ".join(global_blockers)
        ),
        "controls": {
            "refresh_enabled": True,
            "view_enabled": True,
            "configuration_select_enabled": not global_blockers,
            "clear_configuration_enabled": not global_blockers,
            "canonical_activate_enabled": False,
            "human_gate_create_enabled": False,
            "runtime_start_enabled": False,
            "runtime_stop_enabled": False,
            "lifecycle_write_enabled": False,
            "parallel_observation_center_enabled": True,
            "parallel_observation_canonical_connect_enabled": False,
        },
        **SAFETY,
    }
    payload["snapshot_hash"] = canonical_mapping_hash(payload)
    return payload


def evaluate_configuration_selection(
    snapshot: Mapping[str, Any],
    record: Mapping[str, Any],
) -> StrategyChangeDecision:
    blockers = list(_sequence(snapshot.get("global_blockers")))
    strategy_id = _text(record.get("strategy_id"))
    strategy_version = _text(record.get("version"))
    path = _text(record.get("path"))
    if not strategy_id:
        blockers.append("Strategy ID is missing")
    if not strategy_version:
        blockers.append("Strategy version is missing")
    if not bool(record.get("valid", False)):
        blockers.append("Strategy pack validation has not passed")
    if not bool(record.get("paper_only", False)):
        blockers.append("Strategy pack is not paper-only")
    if not path:
        blockers.append("Strategy pack path is missing")

    blockers = list(dict.fromkeys(_text(item) for item in blockers if _text(item)))
    return StrategyChangeDecision(
        allowed=not blockers,
        action="SELECT_PAPER_CONFIGURATION",
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        blockers=tuple(blockers),
        warning=(
            "This changes only the paper strategy configuration. "
            "It does not activate the canonical runtime or create a human gate."
        ),
    )


def evaluate_clear_configuration(
    snapshot: Mapping[str, Any],
) -> StrategyChangeDecision:
    blockers = list(_sequence(snapshot.get("global_blockers")))
    blockers = list(dict.fromkeys(_text(item) for item in blockers if _text(item)))
    selected = _mapping(snapshot.get("selected_configuration"))
    return StrategyChangeDecision(
        allowed=not blockers,
        action="CLEAR_PAPER_CONFIGURATION",
        strategy_id=_text(selected.get("strategy_id")),
        strategy_version=_text(selected.get("strategy_version")),
        blockers=tuple(blockers),
        warning=(
            "This clears only the paper strategy configuration. "
            "It does not stop a runtime, close a position or alter lifecycle evidence."
        ),
    )


def guard_payload() -> dict[str, Any]:
    return {
        "schema_version": PRODUCT_STRATEGY_MANAGER_SCHEMA_VERSION,
        "guard_check_status": "PASS",
        "available_strategy_display": True,
        "selected_strategy_display": True,
        "version_parameter_display": True,
        "validation_status_display": True,
        "runtime_lifecycle_display": True,
        "open_position_switch_blocked": True,
        "runtime_running_switch_blocked": True,
        "configuration_selection_only": True,
        "canonical_activation_separately_human_gated": True,
        "parallel_observation_display": True,
        "parallel_observation_canonical_connection_blocked": True,
        **SAFETY,
    }
