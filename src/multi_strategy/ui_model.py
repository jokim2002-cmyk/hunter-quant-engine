"""Read-only strategy model for a future HQE product UI surface.

The model contains no callbacks, commands, filesystem writes, or runtime
controls. It exposes validated display data only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from src.multi_strategy.activation import DisabledActivationPreflightResult
from src.multi_strategy.errors import ProductUiModelError
from src.multi_strategy.evidence_view import OperatorEvidenceView
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.manifest import StrategyManifest
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot

PRODUCT_UI_MODEL_SCHEMA_VERSION = "1.0.0"


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


@dataclass(frozen=True)
class ReadOnlyProductStrategyUiModel:
    """Validated display-only strategy card for future product integration."""

    strategy_name: str
    strategy_id: str
    strategy_version: str
    implementation_key: str
    parameters: Mapping[str, Any]
    selection_hash: str
    manifest_fingerprint: str
    preflight_status: str
    preflight_hash: str
    evidence_status: str
    evidence_view_hash: str
    runtime_status: str
    runtime_observation_hash: str
    cycle_count: int
    match_count: int
    mismatch_count: int
    blockers: tuple[str, ...]
    schema_version: str = PRODUCT_UI_MODEL_SCHEMA_VERSION
    read_only: bool = True
    selection_enabled: bool = False
    activation_enabled: bool = False
    start_enabled: bool = False
    stop_enabled: bool = False
    runtime_control_enabled: bool = False
    lifecycle_write_enabled: bool = False
    broker_execution_enabled: bool = False
    real_money_enabled: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != PRODUCT_UI_MODEL_SCHEMA_VERSION:
            raise ProductUiModelError("unsupported product UI model schema")
        if not self.strategy_name.strip():
            raise ProductUiModelError("strategy_name is required")
        if self.cycle_count != self.match_count + self.mismatch_count:
            raise ProductUiModelError(
                "cycle_count must equal match plus mismatch counts"
            )
        if not self.read_only:
            raise ProductUiModelError("product strategy model must be read-only")
        if any(
            (
                self.selection_enabled,
                self.activation_enabled,
                self.start_enabled,
                self.stop_enabled,
                self.runtime_control_enabled,
                self.lifecycle_write_enabled,
                self.broker_execution_enabled,
                self.real_money_enabled,
            )
        ):
            raise ProductUiModelError(
                "read-only product strategy model cannot enable controls"
            )
        object.__setattr__(self, "parameters", _freeze(self.parameters))
        object.__setattr__(self, "blockers", tuple(self.blockers))

    @classmethod
    def build(
        cls,
        *,
        manifest: StrategyManifest,
        selection: StrategySelectionSnapshot,
        preflight: DisabledActivationPreflightResult,
        operator_view: OperatorEvidenceView,
        runtime_observation: StableRuntimeObservation,
    ) -> "ReadOnlyProductStrategyUiModel":
        issues: list[str] = []
        if manifest.strategy_id != selection.strategy_id:
            issues.append("manifest strategy_id mismatch")
        if manifest.strategy_version != selection.strategy_version:
            issues.append("manifest strategy_version mismatch")
        if manifest.implementation_key != selection.implementation_key:
            issues.append("manifest implementation_key mismatch")
        if manifest.fingerprint() != selection.manifest_fingerprint:
            issues.append("manifest fingerprint mismatch")
        if preflight.selection_hash != selection.selection_hash:
            issues.append("preflight selection hash mismatch")
        if preflight.operator_view_hash != operator_view.view_hash:
            issues.append("preflight operator view hash mismatch")
        if (
            preflight.runtime_observation_hash
            != runtime_observation.observation_hash
        ):
            issues.append("preflight runtime observation hash mismatch")
        if operator_view.selection_hash != selection.selection_hash:
            issues.append("operator selection hash mismatch")
        if issues:
            raise ProductUiModelError("; ".join(issues))

        return cls(
            strategy_name=manifest.display_name,
            strategy_id=selection.strategy_id,
            strategy_version=selection.strategy_version,
            implementation_key=selection.implementation_key,
            parameters=dict(selection.parameters),
            selection_hash=selection.selection_hash,
            manifest_fingerprint=selection.manifest_fingerprint,
            preflight_status=preflight.status.value,
            preflight_hash=preflight.preflight_hash,
            evidence_status=operator_view.overall_status,
            evidence_view_hash=operator_view.view_hash,
            runtime_status=runtime_observation.runtime_status,
            runtime_observation_hash=runtime_observation.observation_hash,
            cycle_count=operator_view.cycle_count,
            match_count=operator_view.match_count,
            mismatch_count=operator_view.mismatch_count,
            blockers=preflight.blockers,
        )

    @property
    def model_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    @property
    def trader_status(self) -> str:
        if self.preflight_status == "READY_DISABLED":
            return "Evidence ready — activation remains locked"
        return "Not ready — activation remains locked"

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "strategy_name": self.strategy_name,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "implementation_key": self.implementation_key,
            "parameters": dict(self.parameters),
            "selection_hash": self.selection_hash,
            "manifest_fingerprint": self.manifest_fingerprint,
            "preflight_status": self.preflight_status,
            "preflight_hash": self.preflight_hash,
            "evidence_status": self.evidence_status,
            "evidence_view_hash": self.evidence_view_hash,
            "runtime_status": self.runtime_status,
            "runtime_observation_hash": self.runtime_observation_hash,
            "cycle_count": self.cycle_count,
            "match_count": self.match_count,
            "mismatch_count": self.mismatch_count,
            "blockers": list(self.blockers),
            "trader_status": self.trader_status,
            "read_only": True,
            "controls": {
                "selection_enabled": False,
                "activation_enabled": False,
                "start_enabled": False,
                "stop_enabled": False,
                "runtime_control_enabled": False,
                "lifecycle_write_enabled": False,
                "broker_execution_enabled": False,
                "real_money_enabled": False,
            },
        }
        if include_hash:
            payload["model_hash"] = self.model_hash
        return payload

    def render_markdown(self) -> str:
        parameters = "\n".join(
            f"  - {name}: `{value}`"
            for name, value in sorted(self.parameters.items())
        ) or "  - none"
        blockers = "\n".join(f"  - {item}" for item in self.blockers)
        if not blockers:
            blockers = "  - none"
        return (
            "# HQE Strategy Status (Read Only)\n\n"
            f"- Strategy: **{self.strategy_name}**\n"
            f"- Version: `{self.strategy_version}`\n"
            f"- Status: **{self.trader_status}**\n"
            f"- Evidence: **{self.evidence_status}**\n"
            f"- Runtime observed: **{self.runtime_status}**\n"
            f"- Parity: {self.match_count}/{self.cycle_count} match\n\n"
            "## Parameters\n\n"
            f"{parameters}\n\n"
            "## Blockers\n\n"
            f"{blockers}\n\n"
            "## Controls\n\n"
            "- Select strategy: **DISABLED**\n"
            "- Activate strategy: **DISABLED**\n"
            "- Start/stop runtime: **DISABLED**\n"
            "- Real orders: **DISABLED**\n"
            "- Real money: **DISABLED**\n"
        )
