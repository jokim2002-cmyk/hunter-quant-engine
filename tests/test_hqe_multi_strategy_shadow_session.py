from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts import hqe_smc_live_direction as legacy_smc
from scripts.hqe_multi_strategy_flat_copy_dry_run import (
    run_synthetic_dry_run,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.errors import ShadowSessionError
from src.multi_strategy.recorded import RecordedStrategyInput
from src.multi_strategy.recovery import OfflineRestartRecoveryReader
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.session import (
    GuardedShadowSessionController,
    ParityEvidenceEventType,
    ParityEvidenceJournal,
    ShadowSessionStatus,
)
from src.multi_strategy.shadow import OfflineShadowParityRunner


def index_rows(count: int = 30) -> list[dict]:
    rows = []
    for index in range(count):
        base = 24000.0 + index
        rows.append(
            {
                "timestamp": f"2026-07-16 10:{index:02d}:00",
                "open": base,
                "high": base + 10,
                "low": base - 10,
                "close": base + 2,
                "volume": 1000 + index,
            }
        )
    return rows


def premium_rows() -> list[dict]:
    return [
        {
            "timestamp": "2026-07-16 10:29:00",
            "symbol": "NIFTY_SESSION_CE",
            "ltp": 120.0,
            "dte": 2,
        },
        {
            "timestamp": "2026-07-16 10:29:00",
            "symbol": "NIFTY_SESSION_PE",
            "ltp": 95.0,
            "dte": 2,
        },
    ]


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): (
            hashlib.sha256(path.read_bytes()).hexdigest()
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def build_controller(tmp_path: Path):
    payload = run_synthetic_dry_run(tmp_path / "phase4c")
    selection = StrategySelectionSnapshot.from_dict(
        payload["selection"]
    )
    target_root = Path(payload["target_root"])
    recovery = OfflineRestartRecoveryReader(target_root).read(
        selection
    )
    runner = OfflineShadowParityRunner(
        registry=build_phase3_registry(),
        selection=selection,
        recovery=recovery,
    )
    journal = ParityEvidenceJournal(
        tmp_path / "shadow_evidence" / "parity.jsonl"
    )
    controller = GuardedShadowSessionController(
        runner=runner,
        recovery=recovery,
        journal=journal,
        session_id="session-001",
    )
    request = RecordedStrategyInput(
        index_rows=index_rows(),
        premium_rows=premium_rows(),
        er20=0.50,
        symbol="NIFTY",
        timeframe="5m",
    )
    return controller, request, journal, target_root, recovery


def test_guarded_session_journals_three_match_cycles_without_lifecycle_writes(
    tmp_path,
    monkeypatch,
):
    controller, request, journal, target_root, _ = build_controller(
        tmp_path
    )
    before = tree_hashes(target_root)
    controller.start(event_time="2026-07-16T10:00:00+05:30")

    for index, signal in enumerate(("LONG", "SHORT", "NEUTRAL"), start=1):
        direction = 200.0 if signal == "LONG" else (
            -200.0 if signal == "SHORT" else 0.0
        )
        monkeypatch.setattr(
            legacy_smc,
            "_run_gate",
            lambda events, s=signal, d=direction: (
                s,
                f"session_{s.lower()}",
                d,
            ),
        )
        result = controller.run_cycle(
            cycle_id=f"cycle-{index:03d}",
            event_time=f"2026-07-16T10:{index * 5:02d}:00+05:30",
            request=request,
        )
        assert result.registered_result.decision.signal == signal

    controller.close(event_time="2026-07-16T10:20:00+05:30")
    summary = controller.summary()
    records = journal.read_records()

    assert controller.status is ShadowSessionStatus.CLOSED
    assert summary.cycle_count == 3
    assert summary.match_count == 3
    assert summary.mismatch_count == 0
    assert summary.record_count == 5
    assert records[0].event_type is ParityEvidenceEventType.SESSION_STARTED
    assert records[-1].event_type is ParityEvidenceEventType.SESSION_CLOSED
    assert [item.details.get("signal") for item in records[1:4]] == [
        "LONG",
        "SHORT",
        "NEUTRAL",
    ]
    assert summary.summary_hash == controller.summary().summary_hash
    assert tree_hashes(target_root) == before


def test_session_halts_and_journals_parity_mismatch(
    tmp_path,
    monkeypatch,
):
    controller, request, journal, _, _ = build_controller(tmp_path)
    controller.start(event_time="2026-07-16T10:00:00+05:30")
    calls = {"count": 0}

    def changing_gate(events):
        calls["count"] += 1
        if calls["count"] % 2:
            return "LONG", "changing_long", 200.0
        return "SHORT", "changing_short", -200.0

    monkeypatch.setattr(legacy_smc, "_run_gate", changing_gate)
    with pytest.raises(ShadowSessionError, match="halted"):
        controller.run_cycle(
            cycle_id="cycle-mismatch",
            event_time="2026-07-16T10:05:00+05:30",
            request=request,
        )

    assert controller.status is ShadowSessionStatus.HALTED
    records = journal.read_records()
    assert records[-1].event_type is (
        ParityEvidenceEventType.PARITY_MISMATCH
    )
    assert records[-1].mismatch_reasons

    with pytest.raises(ShadowSessionError, match="RUNNING"):
        controller.run_cycle(
            cycle_id="cycle-after-halt",
            event_time="2026-07-16T10:10:00+05:30",
            request=request,
        )

    controller.close(event_time="2026-07-16T10:15:00+05:30")
    assert controller.summary().mismatch_count == 1


def test_session_rejects_journal_inside_strategy_namespace(tmp_path):
    payload = run_synthetic_dry_run(tmp_path / "phase4c")
    selection = StrategySelectionSnapshot.from_dict(
        payload["selection"]
    )
    target_root = Path(payload["target_root"])
    recovery = OfflineRestartRecoveryReader(target_root).read(
        selection
    )
    runner = OfflineShadowParityRunner(
        registry=build_phase3_registry(),
        selection=selection,
        recovery=recovery,
    )
    journal = ParityEvidenceJournal(
        Path(recovery.namespace_directory) / "parity.jsonl"
    )

    with pytest.raises(
        ShadowSessionError,
        match="outside strategy namespace",
    ):
        GuardedShadowSessionController(
            runner=runner,
            recovery=recovery,
            journal=journal,
            session_id="session-001",
        )


def test_session_requires_new_journal_and_refuses_runtime_connection(tmp_path):
    controller, _, journal, _, recovery = build_controller(tmp_path)
    controller.start(event_time="2026-07-16T10:00:00+05:30")

    runner = controller._runner
    with pytest.raises(ShadowSessionError, match="new empty journal"):
        GuardedShadowSessionController(
            runner=runner,
            recovery=recovery,
            journal=journal,
            session_id="session-002",
        )

    fresh = ParityEvidenceJournal(tmp_path / "fresh.jsonl")
    with pytest.raises(ShadowSessionError, match="cannot connect"):
        GuardedShadowSessionController(
            runner=runner,
            recovery=recovery,
            journal=fresh,
            session_id="session-003",
            runtime_connected=True,
        )


def test_session_blocks_cycles_before_start_after_close_and_duplicates(
    tmp_path,
    monkeypatch,
):
    controller, request, _, _, _ = build_controller(tmp_path)
    monkeypatch.setattr(
        legacy_smc,
        "_run_gate",
        lambda events: ("LONG", "stable", 200.0),
    )

    with pytest.raises(ShadowSessionError, match="RUNNING"):
        controller.run_cycle(
            cycle_id="cycle-001",
            event_time="2026-07-16T10:00:00+05:30",
            request=request,
        )

    controller.start(event_time="2026-07-16T10:00:00+05:30")
    controller.run_cycle(
        cycle_id="cycle-001",
        event_time="2026-07-16T10:05:00+05:30",
        request=request,
    )
    with pytest.raises(Exception, match="duplicate cycle_id"):
        controller.run_cycle(
            cycle_id="cycle-001",
            event_time="2026-07-16T10:06:00+05:30",
            request=request,
        )

    controller.close(event_time="2026-07-16T10:10:00+05:30")
    with pytest.raises(ShadowSessionError, match="RUNNING"):
        controller.run_cycle(
            cycle_id="cycle-002",
            event_time="2026-07-16T10:15:00+05:30",
            request=request,
        )
