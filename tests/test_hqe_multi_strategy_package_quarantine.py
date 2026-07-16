from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import src.multi_strategy.quarantine as quarantine_module
from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.errors import PackageQuarantineError
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.quarantine import (
    ImportPreviewStatus,
    OfflineStrategyPackageQuarantine,
)


def _manifest(
    *,
    strategy_id: str = "quarantine_preview",
    strategy_version: str = "1.0.0",
    implementation_key: str = CURRENT_SMC_IMPLEMENTATION_KEY,
    display_name: str = "Quarantine Preview",
) -> StrategyManifest:
    return StrategyManifest(
        strategy_id=strategy_id,
        display_name=display_name,
        strategy_version=strategy_version,
        description="Offline data-only package preview.",
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_package(root: Path, manifest: StrategyManifest) -> None:
    root.mkdir(parents=True)
    manifest_path = root / "manifest.json"
    readme_path = root / "README.md"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    readme_path.write_text("# Offline preview\n", encoding="utf-8")
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


def test_quarantine_copies_exact_data_only_package(tmp_path):
    source = tmp_path / "source"
    quarantine_root = tmp_path / "quarantine"
    _write_package(source, _manifest())

    result = OfflineStrategyPackageQuarantine(
        build_phase3_registry()
    ).quarantine(
        source_root=source,
        quarantine_root=quarantine_root,
    )

    assert result.preview.preview_status is (
        ImportPreviewStatus.PREVIEW_REVIEWED_REFERENCE
    )
    assert result.preview.reviewed_implementation_available is True
    assert result.import_performed is False
    assert result.registry_mutated is False
    assert result.activation_authorized is False
    assert result.runtime_connected is False
    assert result.source_modified is False
    for evidence in result.source_evidence:
        copied = (
            result.quarantined_package_directory
            / evidence.relative_path
        )
        assert _sha256(copied) == evidence.sha256


def test_metadata_only_preview_remains_non_authorizing(tmp_path):
    source = tmp_path / "source"
    _write_package(
        source,
        _manifest(
            implementation_key="hqe.unreviewed.preview_v1",
        ),
    )

    result = OfflineStrategyPackageQuarantine(
        build_phase3_registry()
    ).quarantine(
        source_root=source,
        quarantine_root=tmp_path / "quarantine",
    )

    assert result.preview.preview_status is (
        ImportPreviewStatus.PREVIEW_METADATA_ONLY
    )
    assert result.preview.reviewed_implementation_available is False
    assert result.preview.blockers
    assert result.preview.import_authorized is False


def test_existing_identical_registration_is_previewed_as_duplicate(tmp_path):
    registry = build_phase3_registry()
    current = registry.list_registrations()[0].manifest
    source = tmp_path / "source"
    _write_package(source, current)

    result = OfflineStrategyPackageQuarantine(registry).quarantine(
        source_root=source,
        quarantine_root=tmp_path / "quarantine",
    )

    assert result.preview.preview_status is (
        ImportPreviewStatus.DUPLICATE_EXISTING
    )
    assert result.preview.registration_conflict is False
    assert result.preview.import_authorized is False


def test_existing_different_manifest_is_blocked_conflict(tmp_path):
    registry = build_phase3_registry()
    current = next(
        item.manifest
        for item in registry.list_registrations()
        if item.manifest.strategy_id == "hqe_current_smc_compatibility"
    )
    source = tmp_path / "source"
    conflict = StrategyManifest.from_dict(
        {
            **current.to_dict(),
            "display_name": "Conflicting Name",
        }
    )
    _write_package(source, conflict)

    result = OfflineStrategyPackageQuarantine(registry).quarantine(
        source_root=source,
        quarantine_root=tmp_path / "quarantine",
    )

    assert result.preview.preview_status is (
        ImportPreviewStatus.BLOCKED_ID_VERSION_CONFLICT
    )
    assert result.preview.registration_conflict is True
    assert result.preview.blockers


def test_repeated_quarantine_reuses_verified_record(tmp_path):
    source = tmp_path / "source"
    quarantine_root = tmp_path / "quarantine"
    _write_package(source, _manifest())
    service = OfflineStrategyPackageQuarantine(build_phase3_registry())

    first = service.quarantine(
        source_root=source,
        quarantine_root=quarantine_root,
    )
    second = service.quarantine(
        source_root=source,
        quarantine_root=quarantine_root,
    )

    assert first.reused_existing is False
    assert second.reused_existing is True
    assert (
        first.quarantine_record_directory
        == second.quarantine_record_directory
    )


def test_source_and_quarantine_roots_cannot_overlap(tmp_path):
    source = tmp_path / "source"
    _write_package(source, _manifest())

    with pytest.raises(
        PackageQuarantineError,
        match="must not contain each other",
    ):
        OfflineStrategyPackageQuarantine(
            build_phase3_registry()
        ).quarantine(
            source_root=source,
            quarantine_root=source / "quarantine",
        )


def test_source_change_during_copy_is_detected(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _write_package(source, _manifest())
    real_capture = quarantine_module._capture_package_evidence
    calls = {"count": 0}

    def changing_capture(path):
        calls["count"] += 1
        if calls["count"] == 2 and Path(path).resolve() == source.resolve():
            readme = source / "README.md"
            readme.write_text("# changed\n", encoding="utf-8")
        return real_capture(path)

    monkeypatch.setattr(
        quarantine_module,
        "_capture_package_evidence",
        changing_capture,
    )

    with pytest.raises(
        PackageQuarantineError,
        match="source package changed",
    ):
        OfflineStrategyPackageQuarantine(
            build_phase3_registry()
        ).quarantine(
            source_root=source,
            quarantine_root=tmp_path / "quarantine",
        )
