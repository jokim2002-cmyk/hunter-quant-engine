"""Safe local package validation for HQE strategy manifest packages.

Package format V1 is deliberately data-only. A package references a reviewed
local implementation through ``implementation_key`` and cannot carry Python,
PowerShell, DLL, executable, or shell code.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.multi_strategy.errors import PackageValidationError
from src.multi_strategy.manifest import StrategyManifest

PACKAGE_SCHEMA_VERSION = "1.0.0"
_REQUIRED_FILES = {"manifest.json", "checksums.json"}
_ALLOWED_ROOT_FILES = {
    "manifest.json",
    "checksums.json",
    "README.md",
    "README.txt",
}
_ALLOWED_NESTED_ROOTS = {"docs", "examples"}
_ALLOWED_SUFFIXES = {".json", ".md", ".txt", ".csv"}
_EXECUTABLE_SUFFIXES = {
    ".py",
    ".pyc",
    ".pyd",
    ".dll",
    ".exe",
    ".ps1",
    ".bat",
    ".cmd",
    ".sh",
    ".so",
    ".jar",
    ".msi",
    ".com",
}


@dataclass(frozen=True)
class StrategyPackage:
    """Validated data-only package metadata."""

    root: Path
    manifest: StrategyManifest
    files: tuple[str, ...]
    package_fingerprint: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError(
            (f"{label} is not readable valid JSON: {exc}",)
        ) from exc
    if not isinstance(payload, dict):
        raise PackageValidationError(
            (f"{label} must contain a JSON object",)
        )
    return payload


def _relative_files(root: Path) -> tuple[tuple[Path, str], ...]:
    records: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            records.append((path, relative))
            continue
        if path.is_dir():
            continue
        records.append((path, relative))
    return tuple(records)


def _file_policy_issues(
    records: tuple[tuple[Path, str], ...],
) -> tuple[str, ...]:
    issues: list[str] = []
    for path, relative in records:
        if path.is_symlink():
            issues.append(f"symlinks are not allowed: {relative}")
            continue

        suffix = path.suffix.lower()
        if suffix in _EXECUTABLE_SUFFIXES:
            issues.append(f"executable code is not allowed: {relative}")
            continue
        if suffix not in _ALLOWED_SUFFIXES:
            issues.append(f"unsupported file type: {relative}")
            continue

        parts = Path(relative).parts
        if len(parts) == 1:
            if relative not in _ALLOWED_ROOT_FILES:
                issues.append(f"unexpected root file: {relative}")
        elif parts[0] not in _ALLOWED_NESTED_ROOTS:
            issues.append(f"unexpected package path: {relative}")
    return tuple(issues)


def validate_strategy_package(root: Path) -> StrategyPackage:
    """Validate a package without importing or executing code."""

    root = Path(root)
    if root.is_symlink():
        raise PackageValidationError(
            (f"package root cannot be a symlink: {root}",)
        )
    if not root.is_dir():
        raise PackageValidationError(
            (f"package directory does not exist: {root}",)
        )

    records = _relative_files(root)
    relative_names = {relative for _, relative in records}
    issues = [
        f"missing required package file: {name}"
        for name in sorted(_REQUIRED_FILES - relative_names)
    ]
    issues.extend(_file_policy_issues(records))
    if issues:
        raise PackageValidationError(issues)

    manifest_payload = _read_json(
        root / "manifest.json",
        "manifest.json",
    )
    manifest = StrategyManifest.from_dict(manifest_payload)
    try:
        manifest.require_valid()
    except Exception as exc:
        issue_list = getattr(exc, "issues", (str(exc),))
        raise PackageValidationError(
            tuple(f"manifest: {issue}" for issue in issue_list)
        ) from exc

    checksums_payload = _read_json(
        root / "checksums.json",
        "checksums.json",
    )
    if checksums_payload.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        raise PackageValidationError(
            ("unsupported checksums schema_version",)
        )
    expected = checksums_payload.get("files")
    if not isinstance(expected, dict):
        raise PackageValidationError(
            ("checksums.json files must be an object",)
        )

    checksum_targets = {
        relative
        for _, relative in records
        if relative != "checksums.json"
    }
    expected_names = {str(name) for name in expected}
    checksum_issues: list[str] = []

    for missing in sorted(checksum_targets - expected_names):
        checksum_issues.append(f"missing checksum: {missing}")
    for unexpected in sorted(expected_names - checksum_targets):
        checksum_issues.append(f"unexpected checksum entry: {unexpected}")

    path_by_relative = {
        relative: path
        for path, relative in records
    }
    for relative in sorted(checksum_targets & expected_names):
        wanted = str(expected[relative]).lower()
        actual = _sha256(path_by_relative[relative])
        if wanted != actual:
            checksum_issues.append(
                f"checksum mismatch: {relative}"
            )
    if checksum_issues:
        raise PackageValidationError(checksum_issues)

    package_fingerprint = hashlib.sha256(
        json.dumps(
            {
                "manifest_fingerprint": manifest.fingerprint(),
                "checksums": {
                    name: str(expected[name]).lower()
                    for name in sorted(expected)
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return StrategyPackage(
        root=root.resolve(),
        manifest=manifest,
        files=tuple(sorted(relative_names)),
        package_fingerprint=package_fingerprint,
    )
