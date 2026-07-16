"""Explicit error types for the HQE multi-strategy foundation."""

from __future__ import annotations

from collections.abc import Iterable


class StrategyRegistryError(Exception):
    """Base error for multi-strategy contract and registry failures."""


class ManifestValidationError(StrategyRegistryError, ValueError):
    """Raised when a strategy manifest or parameter snapshot is invalid."""

    def __init__(self, issues: Iterable[str]) -> None:
        self.issues = tuple(str(issue) for issue in issues)
        message = "; ".join(self.issues) or "Strategy manifest is invalid."
        super().__init__(message)


class DuplicateStrategyError(StrategyRegistryError):
    """Raised when the same strategy ID and version is registered twice."""


class UnknownStrategyError(StrategyRegistryError, KeyError):
    """Raised when a requested strategy ID/version is not registered."""


class UnreviewedImplementationError(StrategyRegistryError):
    """Raised when a metadata-only strategy is requested for execution."""


class PackageValidationError(StrategyRegistryError, ValueError):
    """Raised when a local strategy package fails safe validation."""

    def __init__(self, issues: Iterable[str]) -> None:
        self.issues = tuple(str(issue) for issue in issues)
        message = "; ".join(self.issues) or "Strategy package is invalid."
        super().__init__(message)


class SelectionValidationError(StrategyRegistryError, ValueError):
    """Raised when a disabled strategy selection snapshot is invalid."""


class SelectionSwitchBlockedError(StrategyRegistryError):
    """Raised when strategy switching violates a safety invariant."""


class StrategyStorageError(StrategyRegistryError, ValueError):
    """Raised when namespaced strategy storage is unsafe or inconsistent."""

class LegacyMigrationError(StrategyRegistryError, ValueError):
    """Raised when legacy Module 131 evidence cannot be planned safely."""


class LegacyRecoveryError(StrategyRegistryError, ValueError):
    """Raised when a recovery compatibility snapshot is inconsistent."""


class MigrationExecutionDisabledError(StrategyRegistryError):
    """Raised because Phase 4B cannot execute or cut over a migration."""


class FlatStateMigrationError(StrategyRegistryError, ValueError):
    """Raised when Phase 4C isolated flat-state copy is unsafe."""

class RestartRecoveryError(StrategyRegistryError, ValueError):
    """Raised when namespaced restart evidence is missing or inconsistent."""


class ShadowParityError(StrategyRegistryError, ValueError):
    """Raised when offline legacy/registered shadow parity is unsafe."""


class ParityJournalError(StrategyRegistryError, ValueError):
    """Raised when append-only parity evidence is unsafe or inconsistent."""


class ShadowSessionError(StrategyRegistryError, ValueError):
    """Raised when a guarded offline shadow session violates safety."""

class RuntimeShadowHookError(StrategyRegistryError, ValueError):
    """Raised when a read-only product/runtime shadow hook is unsafe."""


class OperatorEvidenceViewError(StrategyRegistryError, ValueError):
    """Raised when an operator parity-evidence view is invalid or unsafe."""


class ActivationPreflightError(StrategyRegistryError, ValueError):
    """Raised when disabled activation evidence is unsafe or inconsistent."""


class ProductUiModelError(StrategyRegistryError, ValueError):
    """Raised when a read-only product strategy model is inconsistent."""


class PackageQuarantineError(StrategyRegistryError, ValueError):
    """Raised when offline package quarantine is unsafe or inconsistent."""


class ImportPreviewError(StrategyRegistryError, ValueError):
    """Raised when a non-authorizing import preview is inconsistent."""


class ReadOnlyCatalogError(StrategyRegistryError, ValueError):
    """Raised when a read-only strategy catalog is inconsistent."""

