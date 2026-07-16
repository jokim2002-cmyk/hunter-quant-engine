"""HQE versioned multi-strategy architecture foundation.

The package remains disconnected from the canonical product paper runtime.
"""

from src.multi_strategy.backtest import (
    RegisteredBacktestPipeline,
    RegisteredBacktestResult,
    write_registered_backtest_metadata,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.contract import (
    ForwardPaperCompatibilityAdapter,
    StrategyFactory,
    StrategyImplementation,
)
from src.multi_strategy.decision import StrategyDecision
from src.multi_strategy.errors import (
    DuplicateStrategyError,
    FlatStateMigrationError,
    LegacyMigrationError,
    LegacyRecoveryError,
    ManifestValidationError,
    MigrationExecutionDisabledError,
    PackageValidationError,
    PackageQuarantineError,
    ImportPreviewError,
    ReadOnlyCatalogError,
    OperatorEvidenceViewError,
    ActivationPreflightError,
    ProductUiModelError,
    ParityJournalError,
    RestartRecoveryError,
    RuntimeShadowHookError,
    ShadowParityError,
    ShadowSessionError,
    SelectionSwitchBlockedError,
    SelectionValidationError,
    StrategyRegistryError,
    StrategyStorageError,
    UnknownStrategyError,
    UnreviewedImplementationError,
)
from src.multi_strategy.execution import (
    ExecutionMode,
    StrategyRunMetadata,
    canonical_mapping_hash,
)

from src.multi_strategy.migration import (
    LEGACY_LEDGER_REQUIRED_COLUMNS,
    MIGRATION_SCHEMA_VERSION,
    RECOVERY_SCHEMA_VERSION,
    LegacyFileEvidence,
    LegacyMigrationPlan,
    LegacyModule131MigrationPlanner,
    LegacyModule131Paths,
    LegacyRecoveryCompatibilitySnapshot,
    LegacyRuntimeObservation,
    MigrationReadiness,
    assert_migration_execution_allowed,
    build_recovery_compatibility_snapshot,
)
from src.multi_strategy.migration_copy import (
    FLAT_COPY_SCHEMA_VERSION,
    LEGACY_ARCHIVE_DIRECTORY,
    FlatStateCopyAuthorization,
    FlatStateCopyResult,
    ReviewedFlatStateCopyExecutor,
)


from src.multi_strategy.recovery import (
    OFFLINE_RECOVERY_SCHEMA_VERSION,
    OfflineRecoveryReadiness,
    OfflineRestartRecoveryReader,
    OfflineRestartRecoverySnapshot,
)
from src.multi_strategy.shadow import (
    SHADOW_PARITY_SCHEMA_VERSION,
    OfflineShadowParityRunner,
    ShadowParityResult,
    ShadowParityStatus,
)



from src.multi_strategy.activation import (
    ACTIVATION_PREFLIGHT_SCHEMA_VERSION,
    ActivationPreflightStatus,
    DisabledActivationPreflight,
    DisabledActivationPreflightResult,
)
from src.multi_strategy.ui_model import (
    PRODUCT_UI_MODEL_SCHEMA_VERSION,
    ReadOnlyProductStrategyUiModel,
)

from src.multi_strategy.runtime_hook import (
    RUNTIME_SHADOW_HOOK_SCHEMA_VERSION,
    ReadOnlyProductRuntimeShadowHook,
    RuntimeShadowHookResult,
    StableRuntimeObservation,
)
from src.multi_strategy.evidence_view import (
    OPERATOR_EVIDENCE_SCHEMA_VERSION,
    OperatorEvidenceView,
    OperatorEvidenceViewReader,
)

from src.multi_strategy.session import (
    PARITY_JOURNAL_SCHEMA_VERSION,
    SHADOW_SESSION_SCHEMA_VERSION,
    GuardedShadowSessionController,
    ParityEvidenceEventType,
    ParityEvidenceJournal,
    ParityEvidenceRecord,
    ShadowSessionStatus,
    ShadowSessionSummary,
)


from src.multi_strategy.quarantine import (
    IMPORT_PREVIEW_SCHEMA_VERSION,
    QUARANTINE_PACKAGE_DIRECTORY,
    QUARANTINE_SCHEMA_VERSION,
    ImportPreviewStatus,
    OfflineStrategyPackageQuarantine,
    PackageFileEvidence,
    QuarantinedStrategyPackage,
    StrategyPackageImportPreview,
    build_import_preview,
)
from src.multi_strategy.catalog_view import (
    READ_ONLY_CATALOG_SCHEMA_VERSION,
    CatalogEntrySource,
    ReadOnlyStrategyCatalog,
    ReadOnlyStrategyCatalogEntry,
)

from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    MANIFEST_SCHEMA_VERSION,
    ParameterSpec,
    StrategyManifest,
)
from src.multi_strategy.package import StrategyPackage, validate_strategy_package
from src.multi_strategy.recorded import (
    RecordedStrategyEvaluationResult,
    RecordedStrategyInput,
    RegisteredRecordedEvaluator,
)
from src.multi_strategy.registry import (
    RegistrationStatus,
    StrategyRegistration,
    StrategyRegistry,
)
from src.multi_strategy.selection import (
    SELECTION_SCHEMA_VERSION,
    SelectionActivationStatus,
    StrategySelectionSnapshot,
)
from src.multi_strategy.storage import (
    LEDGER_COLUMNS,
    LEDGER_SCHEMA_VERSION,
    STATE_SCHEMA_VERSION,
    DisabledStrategyArtifactStore,
    PositionLifecycle,
    StrategyArtifactPaths,
    StrategyLedgerRow,
    StrategyStateSnapshot,
    assert_strategy_switch_allowed,
)

__all__ = [
    "CANONICAL_OPTION_MAPPING",
    "CANONICAL_SIGNALS",
    "LEDGER_COLUMNS",
    "LEDGER_SCHEMA_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "LEGACY_LEDGER_REQUIRED_COLUMNS",
    "MIGRATION_SCHEMA_VERSION",
    "RECOVERY_SCHEMA_VERSION",
    "LegacyFileEvidence",
    "LegacyMigrationError",
    "LegacyMigrationPlan",
    "LegacyModule131MigrationPlanner",
    "LegacyModule131Paths",
    "LegacyRecoveryCompatibilitySnapshot",
    "LegacyRecoveryError",
    "LegacyRuntimeObservation",
    "MigrationExecutionDisabledError",
    "MigrationReadiness",
    "OFFLINE_RECOVERY_SCHEMA_VERSION",
    "ACTIVATION_PREFLIGHT_SCHEMA_VERSION",
    "ActivationPreflightError",
    "ActivationPreflightStatus",
    "DisabledActivationPreflight",
    "DisabledActivationPreflightResult",
    "OPERATOR_EVIDENCE_SCHEMA_VERSION",
    "OperatorEvidenceView",
    "OperatorEvidenceViewError",
    "OperatorEvidenceViewReader",
    "PRODUCT_UI_MODEL_SCHEMA_VERSION",
    "ProductUiModelError",
    "ReadOnlyProductStrategyUiModel",
    "OfflineRecoveryReadiness",
    "OfflineRestartRecoveryReader",
    "OfflineRestartRecoverySnapshot",
    "assert_migration_execution_allowed",
    "build_recovery_compatibility_snapshot",
    "SELECTION_SCHEMA_VERSION",
    "STATE_SCHEMA_VERSION",
    "DisabledStrategyArtifactStore",
    "DuplicateStrategyError",
    "FLAT_COPY_SCHEMA_VERSION",
    "LEGACY_ARCHIVE_DIRECTORY",
    "FlatStateCopyAuthorization",
    "FlatStateCopyResult",
    "FlatStateMigrationError",
    "ExecutionMode",
    "ForwardPaperCompatibilityAdapter",
    "ManifestValidationError",
    "PackageValidationError",
    "PackageQuarantineError",
    "ImportPreviewError",
    "ReadOnlyCatalogError",
    "IMPORT_PREVIEW_SCHEMA_VERSION",
    "QUARANTINE_PACKAGE_DIRECTORY",
    "QUARANTINE_SCHEMA_VERSION",
    "ImportPreviewStatus",
    "OfflineStrategyPackageQuarantine",
    "PackageFileEvidence",
    "QuarantinedStrategyPackage",
    "StrategyPackageImportPreview",
    "build_import_preview",
    "READ_ONLY_CATALOG_SCHEMA_VERSION",
    "CatalogEntrySource",
    "ReadOnlyStrategyCatalog",
    "ReadOnlyStrategyCatalogEntry",
    "PARITY_JOURNAL_SCHEMA_VERSION",
    "ParityEvidenceEventType",
    "ParityEvidenceJournal",
    "ParityEvidenceRecord",
    "ParityJournalError",
    "RestartRecoveryError",
    "RuntimeShadowHookError",
    "RuntimeShadowHookResult",
    "ParameterSpec",
    "PositionLifecycle",
    "RUNTIME_SHADOW_HOOK_SCHEMA_VERSION",
    "ReadOnlyProductRuntimeShadowHook",
    "RecordedStrategyEvaluationResult",
    "RecordedStrategyInput",
    "RegisteredBacktestPipeline",
    "RegisteredBacktestResult",
    "RegisteredRecordedEvaluator",
    "RegistrationStatus",
    "ReviewedFlatStateCopyExecutor",
    "SelectionActivationStatus",
    "SelectionSwitchBlockedError",
    "SelectionValidationError",
    "StrategyArtifactPaths",
    "StrategyDecision",
    "StrategyFactory",
    "StrategyImplementation",
    "StrategyLedgerRow",
    "StrategyManifest",
    "StrategyPackage",
    "StrategyRegistration",
    "StrategyRegistry",
    "StrategyRegistryError",
    "StrategyRunMetadata",
    "SHADOW_PARITY_SCHEMA_VERSION",
    "SHADOW_SESSION_SCHEMA_VERSION",
    "GuardedShadowSessionController",
    "OfflineShadowParityRunner",
    "ShadowParityError",
    "ShadowParityResult",
    "ShadowParityStatus",
    "ShadowSessionError",
    "ShadowSessionStatus",
    "ShadowSessionSummary",
    "StrategySelectionSnapshot",
    "StrategyStateSnapshot",
    "StableRuntimeObservation",
    "StrategyStorageError",
    "UnknownStrategyError",
    "UnreviewedImplementationError",
    "assert_strategy_switch_allowed",
    "build_phase3_registry",
    "canonical_mapping_hash",
    "validate_strategy_package",
    "write_registered_backtest_metadata",
]
