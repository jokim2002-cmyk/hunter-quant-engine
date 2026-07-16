"""In-memory reviewed implementation registry for HQE strategies.

Phase 1 deliberately performs no filesystem writes and is not connected to the
canonical paper runtime.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.multi_strategy.contract import (
    StrategyFactory,
    StrategyImplementation,
)
from src.multi_strategy.errors import (
    DuplicateStrategyError,
    UnknownStrategyError,
    UnreviewedImplementationError,
)
from src.multi_strategy.manifest import StrategyManifest


class RegistrationStatus(str, Enum):
    """Whether a manifest has a reviewed executable implementation."""

    METADATA_ONLY = "METADATA_ONLY"
    EXECUTABLE_REVIEWED = "EXECUTABLE_REVIEWED"


@dataclass(frozen=True)
class StrategyRegistration:
    """One immutable registry entry."""

    manifest: StrategyManifest
    source: str
    status: RegistrationStatus

    @property
    def registration_key(self) -> tuple[str, str]:
        return self.manifest.registration_key


class StrategyRegistry:
    """Central deterministic registry with no dynamic imports."""

    def __init__(
        self,
        reviewed_factories: Mapping[str, StrategyFactory] | None = None,
    ) -> None:
        self._reviewed_factories = dict(reviewed_factories or {})
        self._registrations: dict[
            tuple[str, str],
            StrategyRegistration,
        ] = {}

    def register(
        self,
        manifest: StrategyManifest,
        *,
        source: str = "local",
    ) -> StrategyRegistration:
        manifest.require_valid()
        key = manifest.registration_key
        if key in self._registrations:
            raise DuplicateStrategyError(
                "duplicate strategy registration "
                f"'{manifest.strategy_id}@{manifest.strategy_version}'"
            )

        status = (
            RegistrationStatus.EXECUTABLE_REVIEWED
            if manifest.implementation_key in self._reviewed_factories
            else RegistrationStatus.METADATA_ONLY
        )
        registration = StrategyRegistration(
            manifest=manifest,
            source=str(source),
            status=status,
        )
        self._registrations[key] = registration
        return registration

    def register_many(
        self,
        manifests: Iterable[StrategyManifest],
        *,
        source: str = "local",
    ) -> tuple[StrategyRegistration, ...]:
        pending = tuple(manifests)
        seen: set[tuple[str, str]] = set()
        for manifest in pending:
            manifest.require_valid()
            key = manifest.registration_key
            if key in seen or key in self._registrations:
                raise DuplicateStrategyError(
                    "duplicate strategy registration "
                    f"'{manifest.strategy_id}@{manifest.strategy_version}'"
                )
            seen.add(key)

        return tuple(
            self.register(manifest, source=source)
            for manifest in pending
        )

    def get(
        self,
        strategy_id: str,
        strategy_version: str,
    ) -> StrategyRegistration:
        key = (strategy_id, strategy_version)
        try:
            return self._registrations[key]
        except KeyError as exc:
            raise UnknownStrategyError(
                f"strategy '{strategy_id}@{strategy_version}' "
                "is not registered"
            ) from exc

    def list_registrations(self) -> tuple[StrategyRegistration, ...]:
        return tuple(
            self._registrations[key]
            for key in sorted(self._registrations)
        )

    def create(
        self,
        strategy_id: str,
        strategy_version: str,
        *,
        parameters: Mapping[str, Any] | None = None,
    ) -> StrategyImplementation:
        registration = self.get(strategy_id, strategy_version)
        manifest = registration.manifest
        factory = self._reviewed_factories.get(
            manifest.implementation_key
        )
        if factory is None:
            raise UnreviewedImplementationError(
                "strategy "
                f"'{strategy_id}@{strategy_version}' is metadata-only; "
                "its implementation key has not been reviewed"
            )

        normalized = manifest.validate_parameters(parameters)
        return factory(normalized)
