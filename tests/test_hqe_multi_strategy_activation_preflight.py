from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from scripts.hqe_multi_strategy_runtime_shadow_view_dry_run import (
    run_dry_run as run_phase4f_dry_run,
)
from src.multi_strategy.activation import (
    ActivationPreflightStatus,
    DisabledActivationPreflight,
)
from src.multi_strategy.adapters.current_smc import current_smc_manifest
from src.multi_strategy.evidence_view import OperatorEvidenceViewReader
from src.multi_strategy.errors import ActivationPreflightError
from src.multi_strategy.recovery import OfflineRestartRecoveryReader
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    root = tmp_path_factory.mktemp("phase4g_activation")
    payload = run_phase4f_dry_run(root / "phase4f")
    selection = StrategySelectionSnapshot.from_dict(
        payload["phase4c_copy"]["selection"]
    )
    target_root = Path(payload["phase4c_copy"]["target_root"])
    recovery = OfflineRestartRecoveryReader(target_root).read(selection)
    operator_view = OperatorEvidenceViewReader(
        payload["journal_path"],
        strategy_namespace=recovery.namespace_directory,
    ).read()
    return selection, recovery, operator_view


def observation(status: str, pid: int | None = None):
    payload = {
        "status": status,
        "pid": pid,
        "paper_only": True,
        "broker_execution": False,
    }
    return StableRuntimeObservation(
        observed_at="2026-07-16T11:25:00+05:30",
        runtime_status=status,
        runtime_pid=pid,
        first_read=payload,
        second_read=dict(payload),
    )


def evaluate(evidence, *, status="STOPPED", pid=None, minimum_cycles=3):
    selection, recovery, operator_view = evidence
    return DisabledActivationPreflight(
        minimum_cycles=minimum_cycles
    ).evaluate(
        manifest=current_smc_manifest(),
        selection=selection,
        recovery=recovery,
        operator_view=operator_view,
        runtime_observation=observation(status, pid),
    )


def test_ready_evidence_remains_disabled(evidence):
    result = evaluate(evidence)

    assert result.status is ActivationPreflightStatus.READY_DISABLED
    assert result.blockers == ()
    assert result.activation_authorized is False
    assert result.runtime_connection_authorized is False
    assert result.runtime_cutover_authorized is False
    assert result.state_write_authorized is False
    assert result.ledger_write_authorized is False
    assert result.broker_execution_authorized is False
    assert result.real_money_authorized is False


def test_running_runtime_is_blocked_without_authorization(evidence):
    result = evaluate(evidence, status="RUNNING", pid=4100)

    assert result.status is ActivationPreflightStatus.BLOCKED_RUNTIME_ACTIVE
    assert any("STOPPED or NOT_FOUND" in item for item in result.blockers)
    assert result.activation_authorized is False


def test_insufficient_cycle_requirement_is_blocked(evidence):
    result = evaluate(evidence, minimum_cycles=4)

    assert result.status is ActivationPreflightStatus.BLOCKED_EVIDENCE
    assert any("at least 4" in item for item in result.blockers)


def test_preflight_hash_is_deterministic(evidence):
    first = evaluate(evidence)
    second = evaluate(evidence)

    assert first.to_dict() == second.to_dict()
    assert first.preflight_hash == second.preflight_hash


def test_manifest_identity_mismatch_fails_closed(evidence):
    selection, recovery, operator_view = evidence
    changed = replace(current_smc_manifest(), display_name="Changed Name")

    with pytest.raises(ActivationPreflightError, match="fingerprint"):
        DisabledActivationPreflight().evaluate(
            manifest=changed,
            selection=selection,
            recovery=recovery,
            operator_view=operator_view,
            runtime_observation=observation("STOPPED"),
        )


def test_minimum_cycles_must_be_positive():
    with pytest.raises(ActivationPreflightError, match="positive"):
        DisabledActivationPreflight(minimum_cycles=0)
