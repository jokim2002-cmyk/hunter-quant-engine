"""Synthetic Phase 4H offline package quarantine/catalog dry run."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.catalog_view import ReadOnlyStrategyCatalog
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


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _write_package(
    root: Path,
    *,
    strategy_id: str,
    display_name: str,
    implementation_key: str,
) -> None:
    root.mkdir(parents=True, exist_ok=False)
    manifest = StrategyManifest(
        strategy_id=strategy_id,
        display_name=display_name,
        strategy_version="1.0.0",
        description="Synthetic data-only quarantine preview package.",
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
    example_path = root / "examples" / "parameters.json"
    example_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    readme_path.write_text(
        "# Synthetic offline package preview\n",
        encoding="utf-8",
    )
    example_path.write_text("{}\n", encoding="utf-8")
    (root / "checksums.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "files": {
                    "README.md": _sha256(readme_path),
                    "examples/parameters.json": _sha256(example_path),
                    "manifest.json": _sha256(manifest_path),
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def run(workspace: Path) -> dict:
    workspace = Path(workspace)
    if workspace.exists():
        raise RuntimeError(f"workspace already exists: {workspace}")
    workspace.mkdir(parents=True)

    source_root = workspace / "source_packages"
    reviewed_source = source_root / "reviewed_reference"
    metadata_source = source_root / "metadata_only"
    quarantine_root = workspace / "quarantine"
    catalog_root = workspace / "catalog"

    _write_package(
        reviewed_source,
        strategy_id="hqe_quarantine_reviewed_preview",
        display_name="HQE Quarantine Reviewed Preview",
        implementation_key=CURRENT_SMC_IMPLEMENTATION_KEY,
    )
    _write_package(
        metadata_source,
        strategy_id="hqe_quarantine_metadata_preview",
        display_name="HQE Quarantine Metadata Preview",
        implementation_key="hqe.unreviewed.offline_preview_v1",
    )

    source_before = {
        reviewed_source.name: _tree_hashes(reviewed_source),
        metadata_source.name: _tree_hashes(metadata_source),
    }

    registry = build_phase3_registry()
    service = OfflineStrategyPackageQuarantine(registry)
    reviewed = service.quarantine(
        source_root=reviewed_source,
        quarantine_root=quarantine_root,
    )
    metadata = service.quarantine(
        source_root=metadata_source,
        quarantine_root=quarantine_root,
    )

    source_after = {
        reviewed_source.name: _tree_hashes(reviewed_source),
        metadata_source.name: _tree_hashes(metadata_source),
    }
    source_modified = source_before != source_after
    if source_modified:
        raise RuntimeError("synthetic source packages changed")

    catalog = ReadOnlyStrategyCatalog.build(
        registry=registry,
        quarantined_packages=(reviewed, metadata),
    )
    catalog_root.mkdir(parents=True)
    catalog_json = catalog_root / "strategy_catalog_read_only.json"
    catalog_md = catalog_root / "strategy_catalog_read_only.md"
    catalog_json.write_text(
        json.dumps(catalog.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    catalog_md.write_text(
        catalog.render_markdown() + "\n",
        encoding="utf-8",
    )

    payload = {
        "mode": "OFFLINE_PACKAGE_QUARANTINE_CATALOG_DRY_RUN",
        "workspace": str(workspace),
        "source_modified": False,
        "quarantine_root": str(quarantine_root),
        "quarantined_package_count": 2,
        "quarantined_packages": [
            reviewed.to_dict(),
            metadata.to_dict(),
        ],
        "catalog": catalog.to_dict(),
        "catalog_json_path": str(catalog_json),
        "catalog_json_sha256": _sha256(catalog_json),
        "catalog_markdown_path": str(catalog_md),
        "catalog_markdown_sha256": _sha256(catalog_md),
        "import_performed": False,
        "registry_mutated": False,
        "activation_authorized": False,
        "canonical_runtime_connected": False,
        "runtime_cutover_performed": False,
        "state_written": False,
        "ledger_written": False,
        "broker_execution_performed": False,
        "real_money_authorized": False,
        "module_131_modified": False,
    }
    return payload


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    payload = run(Path(args.workspace))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
