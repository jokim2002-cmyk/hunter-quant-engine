from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.multi_strategy.errors import FlatStateMigrationError
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.migration import (
    LEGACY_LEDGER_REQUIRED_COLUMNS,
    LegacyModule131MigrationPlanner,
    LegacyModule131Paths,
    MigrationReadiness,
)
from src.multi_strategy.migration_copy import (
    FlatStateCopyAuthorization,
    ReviewedFlatStateCopyExecutor,
)
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import (
    LEDGER_COLUMNS,
    PositionLifecycle,
    StrategyArtifactPaths,
    StrategyStateSnapshot,
)


class FakeStrategy:
    def generate(self, context):
        return ()


def selection(strategy_id: str = "flat_copy_test"):
    key = f"hqe.test.{strategy_id}_v1"
    manifest = StrategyManifest(
        strategy_id=strategy_id,
        display_name=strategy_id,
        strategy_version="1.0.0",
        description="test",
        implementation_key=key,
        supported_instruments=("TEST",),
        required_timeframe="5m",
        required_data_columns=("close",),
        warmup_bars=0,
        parameters=(),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    )
    registry = StrategyRegistry({key: lambda parameters: FakeStrategy()})
    return StrategySelectionSnapshot.from_registration(
        registry.register(manifest)
    )


def paths(tmp_path: Path) -> LegacyModule131Paths:
    return LegacyModule131Paths.from_runtime_folder(tmp_path)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def flat_state() -> dict:
    return {
        "status": "FLAT",
        "paper_only": True,
        "module": 131,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "auto_trading_allowed": False,
        "real_money_allowed": False,
    }


def open_state() -> dict:
    return {
        **flat_state(),
        "status": "OPEN",
        "side": "CE_BUY",
        "option_symbol": "NIFTY_TEST_CE",
        "candidate": "SMC_TEST",
        "entry_time": "2026-07-16T10:00:00+05:30",
        "entry": 100.0,
        "stop_loss": 60.0,
        "target": 220.0,
        "quantity": 1,
    }


def ledger_row(event: str) -> dict[str, str]:
    return {
        "timestamp": "2026-07-16T10:00:00+05:30",
        "module": "131",
        "event": event,
        "side": "CE_BUY",
        "option_symbol": "NIFTY_TEST_CE",
        "entry": "100.0",
        "stop_loss": "60.0",
        "target": "220.0",
        "exit_reason": "" if event == "POSITION_OPENED" else "TARGET_HIT",
        "paper_pnl": "0.0" if event == "POSITION_OPENED" else "120.0",
        "paper_only": "True",
    }


def write_ledger(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(LEGACY_LEDGER_REQUIRED_COLUMNS),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def ready_plan(tmp_path: Path):
    selected = selection()
    source = paths(tmp_path / "legacy")
    write_json(source.state, flat_state())
    write_ledger(
        source.ledger,
        [ledger_row("POSITION_OPENED"), ledger_row("POSITION_CLOSED")],
    )
    source.summary.write_text("summary\n", encoding="utf-8")
    source.report.write_text("report\n", encoding="utf-8")
    plan = LegacyModule131MigrationPlanner(
        source,
        selected,
        runtime_confirmed_stopped=True,
    ).build_plan()
    assert plan.readiness is MigrationReadiness.READY_FLAT
    authorization = FlatStateCopyAuthorization.from_plan(
        plan,
        selected,
        runtime_confirmed_stopped=True,
        isolated_storage_confirmed=True,
    )
    return selected, source, plan, authorization


def test_ready_flat_copy_preserves_source_and_creates_namespace(tmp_path):
    selected, source, plan, authorization = ready_plan(tmp_path)
    before = {
        label: Path(evidence.path).read_bytes()
        for label, evidence in plan.evidence.items()
        if evidence.exists
    }
    target = tmp_path / "isolated"
    result = ReviewedFlatStateCopyExecutor(
        target,
        isolated_storage_confirmed=True,
    ).execute(plan, selected, authorization)

    namespace = StrategyArtifactPaths.from_selection(target, selected)
    assert namespace.namespace_directory.is_dir()
    assert result.migration_complete is True
    assert result.dry_run_only is True
    assert result.runtime_connected is False
    assert result.runtime_cutover_performed is False
    assert result.source_modified is False
    assert result.converted_ledger_rows == 2

    state = StrategyStateSnapshot.from_dict(
        json.loads(namespace.state.read_text(encoding="utf-8"))
    )
    assert state.lifecycle is PositionLifecycle.FLAT
    assert state.migration_complete is True
    assert state.matches_selection(selected)

    for label, evidence in plan.evidence.items():
        if evidence.exists:
            original = Path(evidence.path)
            assert original.read_bytes() == before[label]
            archive = (
                namespace.namespace_directory
                / "legacy_source"
                / original.name
            )
            assert archive.read_bytes() == before[label]


def test_converted_ledger_has_identity_and_deterministic_events(tmp_path):
    selected, _, plan, authorization = ready_plan(tmp_path)
    target = tmp_path / "isolated"
    ReviewedFlatStateCopyExecutor(
        target,
        isolated_storage_confirmed=True,
    ).execute(plan, selected, authorization)

    ledger = StrategyArtifactPaths.from_selection(target, selected).ledger
    with ledger.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert tuple(reader.fieldnames or ()) == LEDGER_COLUMNS
    assert [row["lifecycle"] for row in rows] == ["OPEN", "CLOSED"]
    assert rows[0]["event_id"].startswith("legacy-000001-")
    assert rows[1]["event_id"].startswith("legacy-000002-")
    assert all(
        row["selection_hash"] == selected.selection_hash for row in rows
    )
    assert rows[1]["realized_pnl"] == "120.0"


def test_result_and_migration_evidence_are_json_serializable(tmp_path):
    selected, _, plan, authorization = ready_plan(tmp_path)
    target = tmp_path / "isolated"
    result = ReviewedFlatStateCopyExecutor(
        target,
        isolated_storage_confirmed=True,
    ).execute(plan, selected, authorization)
    migration_path = StrategyArtifactPaths.from_selection(
        target, selected
    ).migration

    payload = json.loads(migration_path.read_text(encoding="utf-8"))
    assert payload == result.to_dict()
    assert payload["result_hash"] == result.result_hash
    json.dumps(payload, sort_keys=True)


def test_source_change_after_plan_fails_without_destination(tmp_path):
    selected, source, plan, authorization = ready_plan(tmp_path)
    source.state.write_text(
        json.dumps({**flat_state(), "changed": True}),
        encoding="utf-8",
    )
    target = tmp_path / "isolated"
    executor = ReviewedFlatStateCopyExecutor(
        target,
        isolated_storage_confirmed=True,
    )

    with pytest.raises(FlatStateMigrationError, match="changed"):
        executor.execute(plan, selected, authorization)
    assert not StrategyArtifactPaths.from_selection(
        target, selected
    ).namespace_directory.exists()


def test_open_position_plan_is_rejected(tmp_path):
    selected = selection()
    source = paths(tmp_path / "legacy")
    write_json(source.state, open_state())
    write_ledger(source.ledger, [ledger_row("POSITION_OPENED")])
    plan = LegacyModule131MigrationPlanner(
        source,
        selected,
        runtime_confirmed_stopped=True,
    ).build_plan()
    authorization = FlatStateCopyAuthorization(
        plan_hash=plan.plan_hash,
        selection_hash=selected.selection_hash,
        runtime_confirmed_stopped=True,
        isolated_storage_confirmed=True,
    )

    with pytest.raises(FlatStateMigrationError, match="READY_FLAT"):
        ReviewedFlatStateCopyExecutor(
            tmp_path / "isolated",
            isolated_storage_confirmed=True,
        ).execute(plan, selected, authorization)


def test_no_legacy_data_is_rejected(tmp_path):
    selected = selection()
    source = paths(tmp_path / "legacy")
    plan = LegacyModule131MigrationPlanner(
        source,
        selected,
        runtime_confirmed_stopped=True,
    ).build_plan()
    authorization = FlatStateCopyAuthorization(
        plan_hash=plan.plan_hash,
        selection_hash=selected.selection_hash,
        runtime_confirmed_stopped=True,
        isolated_storage_confirmed=True,
    )

    with pytest.raises(FlatStateMigrationError, match="READY_FLAT"):
        ReviewedFlatStateCopyExecutor(
            tmp_path / "isolated",
            isolated_storage_confirmed=True,
        ).execute(plan, selected, authorization)


def test_authorization_requires_explicit_safety_confirmations(tmp_path):
    selected, _, plan, _ = ready_plan(tmp_path)

    with pytest.raises(FlatStateMigrationError, match="runtime-stopped"):
        FlatStateCopyAuthorization.from_plan(
            plan,
            selected,
            runtime_confirmed_stopped=False,
            isolated_storage_confirmed=True,
        )
    with pytest.raises(FlatStateMigrationError, match="isolated-storage"):
        FlatStateCopyAuthorization.from_plan(
            plan,
            selected,
            runtime_confirmed_stopped=True,
            isolated_storage_confirmed=False,
        )
    with pytest.raises(FlatStateMigrationError, match="isolated storage"):
        ReviewedFlatStateCopyExecutor(
            tmp_path / "isolated",
            isolated_storage_confirmed=False,
        )
    with pytest.raises(FlatStateMigrationError, match="canonical runtime"):
        ReviewedFlatStateCopyExecutor(
            tmp_path / "isolated",
            isolated_storage_confirmed=True,
            runtime_connected=True,
        )


def test_source_and_target_must_be_disjoint(tmp_path):
    selected, source, plan, authorization = ready_plan(tmp_path)
    target_inside_source = source.runtime_folder / "nested_target"

    with pytest.raises(FlatStateMigrationError, match="disjoint"):
        ReviewedFlatStateCopyExecutor(
            target_inside_source,
            isolated_storage_confirmed=True,
        ).execute(plan, selected, authorization)


def test_existing_destination_is_never_overwritten(tmp_path):
    selected, _, plan, authorization = ready_plan(tmp_path)
    target = tmp_path / "isolated"
    namespace = StrategyArtifactPaths.from_selection(target, selected)
    namespace.namespace_directory.mkdir(parents=True)
    marker = namespace.namespace_directory / "keep.txt"
    marker.write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(FlatStateMigrationError, match="already exists"):
        ReviewedFlatStateCopyExecutor(
            target,
            isolated_storage_confirmed=True,
        ).execute(plan, selected, authorization)
    assert marker.read_text(encoding="utf-8") == "do not overwrite"


def test_wrong_plan_or_selection_authorization_is_rejected(tmp_path):
    selected, _, plan, authorization = ready_plan(tmp_path)
    wrong = selection("different_copy_target")

    with pytest.raises(FlatStateMigrationError, match="selection"):
        ReviewedFlatStateCopyExecutor(
            tmp_path / "isolated",
            isolated_storage_confirmed=True,
        ).execute(plan, wrong, authorization)

    bad_authorization = FlatStateCopyAuthorization(
        plan_hash="0" * 64,
        selection_hash=selected.selection_hash,
        runtime_confirmed_stopped=True,
        isolated_storage_confirmed=True,
    )
    with pytest.raises(FlatStateMigrationError, match="authorization"):
        ReviewedFlatStateCopyExecutor(
            tmp_path / "isolated_two",
            isolated_storage_confirmed=True,
        ).execute(plan, selected, bad_authorization)


def test_synthetic_cli_uses_new_external_workspace(tmp_path):
    from scripts.hqe_multi_strategy_flat_copy_dry_run import (
        run_synthetic_dry_run,
    )

    workspace = tmp_path / "phase4c"
    payload = run_synthetic_dry_run(workspace)

    assert payload["mode"] == "ISOLATED_SYNTHETIC_DRY_RUN"
    assert payload["canonical_runtime_connected"] is False
    assert payload["runtime_cutover_performed"] is False
    assert payload["source_modified"] is False
    assert payload["result"]["migration_complete"] is True
    assert payload["result"]["converted_ledger_rows"] == 2

    with pytest.raises(RuntimeError, match="already exists"):
        run_synthetic_dry_run(workspace)
