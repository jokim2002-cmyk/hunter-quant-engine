from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.catalog_view import (
    CatalogEntrySource,
    ReadOnlyStrategyCatalog,
)
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.quarantine import (
    OfflineStrategyPackageQuarantine,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_package(
    root: Path,
    *,
    strategy_id: str,
    implementation_key: str,
) -> None:
    root.mkdir(parents=True)
    manifest = StrategyManifest(
        strategy_id=strategy_id,
        display_name=strategy_id.replace("_", " ").title(),
        strategy_version="1.0.0",
        description="Catalog preview.",
        implementation_key=implementation_key,
        supported_instruments=("NIFTY_INDEX_OPTION_BUY",),
        required_timeframe="5m",
        required_data_columns=(
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ),
        warmup_bars=20,
        parameters=(),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    )
    manifest_path = root / "manifest.json"
    readme_path = root / "README.md"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    readme_path.write_text("# Catalog preview\n", encoding="utf-8")
    (root / "checksums.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "files": {
                    "README.md": _sha256(readme_path),
                    "manifest.json": _sha256(manifest_path),
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _catalog(tmp_path) -> ReadOnlyStrategyCatalog:
    registry = build_phase3_registry()
    service = OfflineStrategyPackageQuarantine(registry)

    reviewed_source = tmp_path / "reviewed"
    metadata_source = tmp_path / "metadata"
    _write_package(
        reviewed_source,
        strategy_id="catalog_reviewed_preview",
        implementation_key=CURRENT_SMC_IMPLEMENTATION_KEY,
    )
    _write_package(
        metadata_source,
        strategy_id="catalog_metadata_preview",
        implementation_key="hqe.unreviewed.catalog_v1",
    )

    reviewed = service.quarantine(
        source_root=reviewed_source,
        quarantine_root=tmp_path / "quarantine",
    )
    metadata = service.quarantine(
        source_root=metadata_source,
        quarantine_root=tmp_path / "quarantine",
    )
    return ReadOnlyStrategyCatalog.build(
        registry=registry,
        quarantined_packages=(reviewed, metadata),
    )


def test_catalog_combines_builtin_and_quarantine_entries(tmp_path):
    catalog = _catalog(tmp_path)

    assert len(catalog.entries) == 4
    assert {
        entry.source
        for entry in catalog.entries
    } == {
        CatalogEntrySource.BUILTIN,
        CatalogEntrySource.QUARANTINE,
    }
    identities = [
        (
            entry.strategy_id,
            entry.strategy_version,
            entry.source.value,
        )
        for entry in catalog.entries
    ]
    assert identities == sorted(identities)


def test_catalog_controls_are_all_disabled(tmp_path):
    payload = _catalog(tmp_path).to_dict()

    assert payload["read_only"] is True
    assert not any(payload["controls"].values())
    assert all(
        not any(entry["controls"].values())
        for entry in payload["entries"]
    )


def test_quarantine_entries_are_not_registered(tmp_path):
    catalog = _catalog(tmp_path)
    quarantine_entries = [
        entry
        for entry in catalog.entries
        if entry.source is CatalogEntrySource.QUARANTINE
    ]

    assert all(
        entry.registration_status == "NOT_REGISTERED"
        for entry in quarantine_entries
    )
    assert {
        entry.preview_status
        for entry in quarantine_entries
    } == {
        "PREVIEW_METADATA_ONLY",
        "PREVIEW_REVIEWED_REFERENCE",
    }


def test_catalog_hash_is_deterministic(tmp_path):
    first = _catalog(tmp_path / "first")
    second = _catalog(tmp_path / "second")

    assert first.catalog_hash == second.catalog_hash


def test_catalog_markdown_is_read_only(tmp_path):
    report = _catalog(tmp_path).render_markdown()

    assert "HQE Strategy Catalog (Read Only)" in report
    assert "Import: **DISABLED**" in report
    assert "Activation: **DISABLED**" in report
    assert "Controls: **ALL DISABLED**" in report
