"""Immutable execution identity for HQE registered strategy runs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from src.multi_strategy.manifest import StrategyManifest
from src.multi_strategy.registry import StrategyRegistration


class ExecutionMode(str, Enum):
    """Supported strategy evaluation modes."""

    BACKTEST = "BACKTEST"
    RECORDED_REPLAY = "RECORDED_REPLAY"
    FORWARD_PAPER = "FORWARD_PAPER"


def canonical_mapping_hash(payload: Mapping[str, Any]) -> str:
    """Return a deterministic SHA-256 for a JSON-compatible mapping."""

    encoded = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _freeze_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return an immutable shallow copy for metadata snapshots."""

    return MappingProxyType(dict(payload))


@dataclass(frozen=True)
class StrategyRunMetadata:
    """Versioned strategy identity attached to one execution result."""

    strategy_id: str
    strategy_version: str
    implementation_key: str
    manifest_fingerprint: str
    parameters: Mapping[str, Any]
    parameters_hash: str
    execution_mode: ExecutionMode
    symbol: str
    timeframe: str
    data_identity: str
    data_start: str | None = None
    data_end: str | None = None

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("strategy_id is required")
        if not self.strategy_version:
            raise ValueError("strategy_version is required")
        if not self.implementation_key:
            raise ValueError("implementation_key is required")
        if not self.symbol:
            raise ValueError("symbol is required")
        if not self.timeframe:
            raise ValueError("timeframe is required")
        if not self.data_identity:
            raise ValueError("data_identity is required")
        object.__setattr__(
            self,
            "parameters",
            _freeze_mapping(self.parameters),
        )

    @classmethod
    def from_registration(
        cls,
        registration: StrategyRegistration,
        *,
        parameters: Mapping[str, Any],
        execution_mode: ExecutionMode,
        symbol: str,
        timeframe: str,
        data_identity: str,
        data_start: str | None = None,
        data_end: str | None = None,
    ) -> "StrategyRunMetadata":
        manifest: StrategyManifest = registration.manifest
        normalized = manifest.validate_parameters(parameters)
        return cls(
            strategy_id=manifest.strategy_id,
            strategy_version=manifest.strategy_version,
            implementation_key=manifest.implementation_key,
            manifest_fingerprint=manifest.fingerprint(),
            parameters=normalized,
            parameters_hash=canonical_mapping_hash(normalized),
            execution_mode=execution_mode,
            symbol=str(symbol),
            timeframe=str(timeframe),
            data_identity=str(data_identity),
            data_start=data_start,
            data_end=data_end,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready immutable metadata snapshot."""

        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "implementation_key": self.implementation_key,
            "manifest_fingerprint": self.manifest_fingerprint,
            "parameters": dict(self.parameters),
            "parameters_hash": self.parameters_hash,
            "execution_mode": self.execution_mode.value,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "data_identity": self.data_identity,
            "data_start": self.data_start,
            "data_end": self.data_end,
        }
