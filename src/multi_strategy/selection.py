"""Disabled immutable strategy selection snapshots for HQE.

Phase 4A snapshots are configuration evidence only. They are not consumed by
or connected to the canonical product paper runtime.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from src.multi_strategy.errors import (
    SelectionValidationError,
    UnreviewedImplementationError,
)
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.registry import (
    RegistrationStatus,
    StrategyRegistration,
)

SELECTION_SCHEMA_VERSION = "1.0.0"


class SelectionActivationStatus(str, Enum):
    """Runtime activation is deliberately disabled in this phase."""

    DISABLED = "DISABLED"


def _freeze_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def _selection_hash_payload(
    *,
    strategy_id: str,
    strategy_version: str,
    implementation_key: str,
    manifest_fingerprint: str,
    parameters_hash: str,
) -> dict[str, str]:
    return {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "strategy_version": strategy_version,
        "implementation_key": implementation_key,
        "manifest_fingerprint": manifest_fingerprint,
        "parameters_hash": parameters_hash,
        "activation_status": SelectionActivationStatus.DISABLED.value,
        "runtime_connected": "false",
    }


def _selection_hash(**kwargs: str) -> str:
    encoded = json.dumps(
        _selection_hash_payload(**kwargs),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class StrategySelectionSnapshot:
    """One deterministic, disabled strategy/parameter selection."""

    strategy_id: str
    strategy_version: str
    implementation_key: str
    manifest_fingerprint: str
    parameters: Mapping[str, Any]
    parameters_hash: str
    activation_status: SelectionActivationStatus = (
        SelectionActivationStatus.DISABLED
    )
    runtime_connected: bool = False
    schema_version: str = SELECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        issues: list[str] = []
        for label, value in (
            ("strategy_id", self.strategy_id),
            ("strategy_version", self.strategy_version),
            ("implementation_key", self.implementation_key),
            ("manifest_fingerprint", self.manifest_fingerprint),
            ("parameters_hash", self.parameters_hash),
        ):
            if not str(value).strip():
                issues.append(f"{label} is required")
        if self.schema_version != SELECTION_SCHEMA_VERSION:
            issues.append(
                f"unsupported selection schema_version '{self.schema_version}'"
            )
        if self.activation_status is not SelectionActivationStatus.DISABLED:
            issues.append("selection activation must remain DISABLED")
        if self.runtime_connected:
            issues.append("selection must not be connected to runtime")
        calculated_parameters_hash = canonical_mapping_hash(self.parameters)
        if self.parameters_hash != calculated_parameters_hash:
            issues.append("parameters_hash does not match parameters")
        if issues:
            raise SelectionValidationError(issues)
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))

    @classmethod
    def from_registration(
        cls,
        registration: StrategyRegistration,
        parameters: Mapping[str, Any] | None = None,
    ) -> "StrategySelectionSnapshot":
        if registration.status is not RegistrationStatus.EXECUTABLE_REVIEWED:
            manifest = registration.manifest
            raise UnreviewedImplementationError(
                "selection requires a reviewed executable strategy; "
                f"'{manifest.strategy_id}@{manifest.strategy_version}' "
                "is metadata-only"
            )
        manifest = registration.manifest
        normalized = manifest.validate_parameters(parameters)
        return cls(
            strategy_id=manifest.strategy_id,
            strategy_version=manifest.strategy_version,
            implementation_key=manifest.implementation_key,
            manifest_fingerprint=manifest.fingerprint(),
            parameters=normalized,
            parameters_hash=canonical_mapping_hash(normalized),
        )

    @property
    def selection_hash(self) -> str:
        return _selection_hash(
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            implementation_key=self.implementation_key,
            manifest_fingerprint=self.manifest_fingerprint,
            parameters_hash=self.parameters_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "selection_hash": self.selection_hash,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "implementation_key": self.implementation_key,
            "manifest_fingerprint": self.manifest_fingerprint,
            "parameters": dict(self.parameters),
            "parameters_hash": self.parameters_hash,
            "activation_status": self.activation_status.value,
            "runtime_connected": self.runtime_connected,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "StrategySelectionSnapshot":
        raw_parameters = payload.get("parameters", {})
        if not isinstance(raw_parameters, Mapping):
            raise SelectionValidationError(("parameters must be a mapping",))
        try:
            activation = SelectionActivationStatus(
                str(payload.get("activation_status", ""))
            )
        except ValueError as exc:
            raise SelectionValidationError(
                ("activation_status must be DISABLED",)
            ) from exc
        snapshot = cls(
            schema_version=str(payload.get("schema_version", "")),
            strategy_id=str(payload.get("strategy_id", "")),
            strategy_version=str(payload.get("strategy_version", "")),
            implementation_key=str(payload.get("implementation_key", "")),
            manifest_fingerprint=str(
                payload.get("manifest_fingerprint", "")
            ),
            parameters=dict(raw_parameters),
            parameters_hash=str(payload.get("parameters_hash", "")),
            activation_status=activation,
            runtime_connected=bool(payload.get("runtime_connected", False)),
        )
        supplied_hash = str(payload.get("selection_hash", ""))
        if supplied_hash and supplied_hash != snapshot.selection_hash:
            raise SelectionValidationError(
                ("selection_hash does not match selection contents",)
            )
        return snapshot
