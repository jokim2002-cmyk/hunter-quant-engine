from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.multi_strategy.errors import PackageValidationError
from src.multi_strategy.package import validate_strategy_package

from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    ParameterSpec,
    StrategyManifest,
)


def sample_manifest(
    *,
    strategy_id: str = "sample_smc",
    strategy_version: str = "1.0.0",
    implementation_key: str = "hqe.reviewed.sample_smc",
) -> StrategyManifest:
    return StrategyManifest(
        strategy_id=strategy_id,
        display_name="Sample SMC",
        strategy_version=strategy_version,
        description="Deterministic paper-only test strategy.",
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
        parameters=(
            ParameterSpec(
                name="er20_min",
                value_type="number",
                default=0.30,
                minimum=0.0,
                maximum=1.0,
            ),
            ParameterSpec(
                name="minimum_dte",
                value_type="integer",
                default=1,
                minimum=0,
                maximum=30,
            ),
            ParameterSpec(
                name="mode",
                value_type="choice",
                default="strict",
                choices=("strict", "relaxed"),
            ),
        ),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    )

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_valid_package(root: Path) -> None:
    root.mkdir(parents=True)
    manifest_path = root / "manifest.json"
    readme_path = root / "README.md"
    example_path = root / "examples" / "parameters.json"
    example_path.parent.mkdir(parents=True)

    manifest_path.write_text(
        json.dumps(
            sample_manifest().to_dict(),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    readme_path.write_text(
        "# Sample strategy package\n",
        encoding="utf-8",
    )
    example_path.write_text(
        '{"er20_min": 0.30}\n',
        encoding="utf-8",
    )
    checksums = {
        "schema_version": "1.0.0",
        "files": {
            "README.md": sha256(readme_path),
            "examples/parameters.json": sha256(example_path),
            "manifest.json": sha256(manifest_path),
        },
    }
    (root / "checksums.json").write_text(
        json.dumps(checksums, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def test_valid_data_only_package_is_accepted(tmp_path):
    package_root = tmp_path / "package"
    write_valid_package(package_root)

    package = validate_strategy_package(package_root)

    assert package.manifest.strategy_id == "sample_smc"
    assert package.package_fingerprint
    assert "manifest.json" in package.files


def test_executable_strategy_code_is_rejected(tmp_path):
    package_root = tmp_path / "package"
    write_valid_package(package_root)
    (package_root / "implementation.py").write_text(
        "raise RuntimeError('must never execute')\n",
        encoding="utf-8",
    )

    with pytest.raises(
        PackageValidationError,
        match="executable code is not allowed",
    ):
        validate_strategy_package(package_root)


def test_checksum_mismatch_is_rejected(tmp_path):
    package_root = tmp_path / "package"
    write_valid_package(package_root)
    (package_root / "README.md").write_text(
        "# changed after checksums\n",
        encoding="utf-8",
    )

    with pytest.raises(
        PackageValidationError,
        match="checksum mismatch",
    ):
        validate_strategy_package(package_root)


def test_unexpected_checksum_entry_is_rejected(tmp_path):
    package_root = tmp_path / "package"
    write_valid_package(package_root)
    checksums_path = package_root / "checksums.json"
    payload = json.loads(checksums_path.read_text(encoding="utf-8"))
    payload["files"]["missing.txt"] = "0" * 64
    checksums_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(
        PackageValidationError,
        match="unexpected checksum entry",
    ):
        validate_strategy_package(package_root)
