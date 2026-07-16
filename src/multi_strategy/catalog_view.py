"""Read-only catalog for built-in and quarantined strategy metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.multi_strategy.errors import ReadOnlyCatalogError
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.quarantine import QuarantinedStrategyPackage
from src.multi_strategy.registry import StrategyRegistry

READ_ONLY_CATALOG_SCHEMA_VERSION = "1.0.0"


class CatalogEntrySource(str, Enum):
    """Origin of one read-only catalog item."""

    BUILTIN = "BUILTIN"
    QUARANTINE = "QUARANTINE"


@dataclass(frozen=True)
class ReadOnlyStrategyCatalogEntry:
    """Display-only strategy catalog entry."""

    source: CatalogEntrySource
    strategy_id: str
    strategy_version: str
    display_name: str
    implementation_key: str
    manifest_fingerprint: str
    registration_status: str
    package_fingerprint: str = ""
    preview_status: str = ""
    blockers: tuple[str, ...] = ()
    schema_version: str = READ_ONLY_CATALOG_SCHEMA_VERSION
    read_only: bool = True
    import_enabled: bool = False
    registration_enabled: bool = False
    selection_enabled: bool = False
    activation_enabled: bool = False
    runtime_control_enabled: bool = False
    broker_execution_enabled: bool = False
    real_money_enabled: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != READ_ONLY_CATALOG_SCHEMA_VERSION:
            raise ReadOnlyCatalogError("unsupported catalog entry schema")
        if not self.strategy_id or not self.strategy_version:
            raise ReadOnlyCatalogError("catalog strategy identity is required")
        if not self.read_only:
            raise ReadOnlyCatalogError("catalog entry must be read-only")
        if any(
            (
                self.import_enabled,
                self.registration_enabled,
                self.selection_enabled,
                self.activation_enabled,
                self.runtime_control_enabled,
                self.broker_execution_enabled,
                self.real_money_enabled,
            )
        ):
            raise ReadOnlyCatalogError(
                "read-only catalog entry cannot enable controls"
            )
        object.__setattr__(self, "blockers", tuple(self.blockers))

    @property
    def entry_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "source": self.source.value,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "display_name": self.display_name,
            "implementation_key": self.implementation_key,
            "manifest_fingerprint": self.manifest_fingerprint,
            "registration_status": self.registration_status,
            "package_fingerprint": self.package_fingerprint,
            "preview_status": self.preview_status,
            "blockers": list(self.blockers),
            "read_only": True,
            "controls": {
                "import_enabled": False,
                "registration_enabled": False,
                "selection_enabled": False,
                "activation_enabled": False,
                "runtime_control_enabled": False,
                "broker_execution_enabled": False,
                "real_money_enabled": False,
            },
        }
        if include_hash:
            payload["entry_hash"] = self.entry_hash
        return payload


@dataclass(frozen=True)
class ReadOnlyStrategyCatalog:
    """Immutable combined built-in/quarantine catalog."""

    entries: tuple[ReadOnlyStrategyCatalogEntry, ...]
    schema_version: str = READ_ONLY_CATALOG_SCHEMA_VERSION
    read_only: bool = True
    import_enabled: bool = False
    activation_enabled: bool = False
    runtime_control_enabled: bool = False
    broker_execution_enabled: bool = False
    real_money_enabled: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != READ_ONLY_CATALOG_SCHEMA_VERSION:
            raise ReadOnlyCatalogError("unsupported catalog schema")
        if not self.read_only:
            raise ReadOnlyCatalogError("catalog must be read-only")
        if any(
            (
                self.import_enabled,
                self.activation_enabled,
                self.runtime_control_enabled,
                self.broker_execution_enabled,
                self.real_money_enabled,
            )
        ):
            raise ReadOnlyCatalogError(
                "read-only catalog cannot enable controls"
            )
        object.__setattr__(self, "entries", tuple(self.entries))

    @classmethod
    def build(
        cls,
        *,
        registry: StrategyRegistry,
        quarantined_packages: tuple[QuarantinedStrategyPackage, ...] = (),
    ) -> "ReadOnlyStrategyCatalog":
        entries: list[ReadOnlyStrategyCatalogEntry] = []

        for registration in registry.list_registrations():
            manifest = registration.manifest
            entries.append(
                ReadOnlyStrategyCatalogEntry(
                    source=CatalogEntrySource.BUILTIN,
                    strategy_id=manifest.strategy_id,
                    strategy_version=manifest.strategy_version,
                    display_name=manifest.display_name,
                    implementation_key=manifest.implementation_key,
                    manifest_fingerprint=manifest.fingerprint(),
                    registration_status=registration.status.value,
                )
            )

        for quarantined in quarantined_packages:
            manifest = quarantined.manifest
            preview = quarantined.preview
            entries.append(
                ReadOnlyStrategyCatalogEntry(
                    source=CatalogEntrySource.QUARANTINE,
                    strategy_id=manifest.strategy_id,
                    strategy_version=manifest.strategy_version,
                    display_name=manifest.display_name,
                    implementation_key=manifest.implementation_key,
                    manifest_fingerprint=manifest.fingerprint(),
                    registration_status="NOT_REGISTERED",
                    package_fingerprint=(
                        quarantined.package_fingerprint
                    ),
                    preview_status=preview.preview_status.value,
                    blockers=preview.blockers,
                )
            )

        entries.sort(
            key=lambda item: (
                item.strategy_id,
                item.strategy_version,
                item.source.value,
                item.package_fingerprint,
            )
        )
        return cls(entries=tuple(entries))

    @property
    def catalog_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "read_only": True,
            "entry_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
            "controls": {
                "import_enabled": False,
                "activation_enabled": False,
                "runtime_control_enabled": False,
                "broker_execution_enabled": False,
                "real_money_enabled": False,
            },
        }
        if include_hash:
            payload["catalog_hash"] = self.catalog_hash
        return payload

    def render_markdown(self) -> str:
        lines = [
            "# HQE Strategy Catalog (Read Only)",
            "",
            "- Import: **DISABLED**",
            "- Registration: **DISABLED**",
            "- Activation: **DISABLED**",
            "- Runtime control: **DISABLED**",
            "- Broker execution: **DISABLED**",
            "- Real money: **DISABLED**",
            "",
            "## Entries",
            "",
        ]
        for entry in self.entries:
            lines.extend(
                [
                    (
                        f"### {entry.display_name} "
                        f"(`{entry.strategy_id}@{entry.strategy_version}`)"
                    ),
                    f"- Source: `{entry.source.value}`",
                    (
                        "- Registration: "
                        f"`{entry.registration_status}`"
                    ),
                    (
                        "- Preview: "
                        f"`{entry.preview_status or 'N/A'}`"
                    ),
                    "- Controls: **ALL DISABLED**",
                    "",
                ]
            )
        return "\n".join(lines)
