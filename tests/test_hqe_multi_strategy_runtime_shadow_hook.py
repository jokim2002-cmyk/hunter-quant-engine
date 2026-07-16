from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.multi_strategy.errors import RuntimeShadowHookError, ShadowSessionError
from src.multi_strategy.runtime_hook import (
    ReadOnlyProductRuntimeShadowHook,
    StableRuntimeObservation,
)
from src.multi_strategy.session import (
    ParityEvidenceEventType,
    ShadowSessionStatus,
)
from src.multi_strategy.shadow import ShadowParityStatus


class FakeController:
    def __init__(self):
        self.status = ShadowSessionStatus.RUNNING
        self.details = None
        self.record = None

    def run_cycle(self, **kwargs):
        self.details = kwargs["evidence_details"]
        decision = SimpleNamespace(signal="LONG", option_side="CE_BUY")
        registered = SimpleNamespace(decision=decision)
        return SimpleNamespace(
            result_hash="parity-result-hash",
            status=ShadowParityStatus.MATCH,
            registered_result=registered,
        )

    def journal_records(self):
        self.record = SimpleNamespace(
            event_type=ParityEvidenceEventType.PARITY_MATCH,
            cycle_id="cycle-001",
            details=dict(self.details),
            record_hash="journal-record-hash",
        )
        return (self.record,)


def observation(**overrides):
    payload = {"status": "RUNNING", "pid": 4100, "paper_only": True}
    values = {
        "observed_at": "2026-07-16T11:05:00+05:30",
        "runtime_status": "RUNNING",
        "runtime_pid": 4100,
        "first_read": payload,
        "second_read": dict(payload),
    }
    values.update(overrides)
    return StableRuntimeObservation(**values)


def test_stable_observation_is_deterministic_and_read_only():
    first = observation()
    second = observation()

    assert first.observation_hash == second.observation_hash
    assert first.payload_hash == second.payload_hash
    assert first.to_dict()["runtime_connected"] is False
    with pytest.raises(TypeError):
        first.first_read["status"] = "STOPPED"


def test_unstable_observation_fails_closed():
    with pytest.raises(RuntimeShadowHookError, match="unstable"):
        observation(second_read={"status": "STOPPED", "pid": 4100})


def test_observation_forbids_runtime_or_write_authority():
    with pytest.raises(RuntimeShadowHookError, match="cannot connect"):
        observation(runtime_control_authorized=True)


def test_hook_binds_observation_hash_to_parity_journal_details():
    controller = FakeController()
    hook = ReadOnlyProductRuntimeShadowHook(controller=controller)
    current = observation()

    result = hook.observe_cycle(
        cycle_id="cycle-001",
        event_time=current.observed_at,
        observation=current,
        request=object(),
    )

    assert controller.details["runtime_observation_hash"] == current.observation_hash
    assert controller.details["runtime_status_observed"] == "RUNNING"
    assert result.journal_record_hash == "journal-record-hash"
    assert result.to_dict()["signal"] == "LONG"
    assert result.to_dict()["state_written"] is False


def test_hook_requires_running_session_and_matching_event_time():
    controller = FakeController()
    controller.status = ShadowSessionStatus.CREATED
    hook = ReadOnlyProductRuntimeShadowHook(controller=controller)
    current = observation()

    with pytest.raises(RuntimeShadowHookError, match="RUNNING"):
        hook.observe_cycle(
            cycle_id="cycle-001",
            event_time=current.observed_at,
            observation=current,
            request=object(),
        )

    controller.status = ShadowSessionStatus.RUNNING
    with pytest.raises(RuntimeShadowHookError, match="time"):
        hook.observe_cycle(
            cycle_id="cycle-001",
            event_time="2026-07-16T11:06:00+05:30",
            observation=current,
            request=object(),
        )


def test_session_evidence_details_cannot_override_safety_keys():
    from src.multi_strategy.session import GuardedShadowSessionController

    controller = object.__new__(GuardedShadowSessionController)
    controller._status = ShadowSessionStatus.RUNNING
    controller._runner = SimpleNamespace(
        run=lambda request: SimpleNamespace(
            selection_hash="selection",
            recovery_snapshot_hash="recovery",
            status=ShadowParityStatus.MATCH,
            result_hash="result",
            input_identity="input",
            mismatch_reasons=(),
            execution_mode=SimpleNamespace(value="FORWARD_PAPER"),
            registered_result=SimpleNamespace(
                decision=SimpleNamespace(signal="LONG", option_side="CE_BUY")
            ),
        )
    )
    controller._recovery = SimpleNamespace(
        selection=SimpleNamespace(selection_hash="selection"),
        snapshot_hash="recovery",
    )
    controller._journal = SimpleNamespace(append=lambda **kwargs: None)
    controller._session_id = "session"

    with pytest.raises(ShadowSessionError, match="protected keys"):
        controller.run_cycle(
            cycle_id="cycle-001",
            event_time="2026-07-16T11:05:00+05:30",
            request=object(),
            evidence_details={"state_written": True},
        )
