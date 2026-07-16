from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts import hqe_smc_live_direction as legacy_smc
from scripts.hqe_multi_strategy_flat_copy_dry_run import (
    run_synthetic_dry_run,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.errors import ShadowParityError
from src.multi_strategy.recorded import RecordedStrategyInput
from src.multi_strategy.recovery import OfflineRestartRecoveryReader
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.shadow import (
    OfflineShadowParityRunner,
    ShadowParityStatus,
)


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
            "symbol": "NIFTY_SHADOW_CE",
            "ltp": 120.0,
            "dte": 2,
        },
        {
            "timestamp": "2026-07-16 10:29:00",
            "symbol": "NIFTY_SHADOW_PE",
            "ltp": 95.0,
            "dte": 2,
        },
    ]


def build_runner(tmp_path: Path):
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
    request = RecordedStrategyInput(
        index_rows=index_rows(),
        premium_rows=premium_rows(),
        er20=0.50,
        symbol="NIFTY",
        timeframe="5m",
    )
    return runner, request, target_root, selection, recovery


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): (
            hashlib.sha256(path.read_bytes()).hexdigest()
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_shadow_parity_matches_and_does_not_write_state(tmp_path, monkeypatch):
    runner, request, target_root, selection, recovery = build_runner(
        tmp_path
    )
    monkeypatch.setattr(
        legacy_smc,
        "_run_gate",
        lambda events: ("LONG", "shadow_long", 200.0),
    )
    before = tree_hashes(target_root)

    result = runner.run(request).require_match()

    assert result.status is ShadowParityStatus.MATCH
    assert result.selection_hash == selection.selection_hash
    assert result.recovery_snapshot_hash == recovery.snapshot_hash
    assert result.registered_result.decision.signal == "LONG"
    assert result.registered_result.decision.option_side == "CE_BUY"
    assert result.registered_result.decision.to_legacy_payload() == (
        dict(result.legacy_payload)
    )
    assert result.runtime_connected is False
    assert result.runtime_cutover_performed is False
    assert result.state_written is False
    assert result.ledger_written is False
    assert tree_hashes(target_root) == before


def test_shadow_parity_short_and_neutral_paths(tmp_path, monkeypatch):
    runner, request, _, _, _ = build_runner(tmp_path)

    monkeypatch.setattr(
        legacy_smc,
        "_run_gate",
        lambda events: ("SHORT", "shadow_short", -200.0),
    )
    short = runner.run(request).require_match()
    assert short.registered_result.decision.signal == "SHORT"
    assert short.registered_result.decision.option_side == "PE_BUY"

    monkeypatch.setattr(
        legacy_smc,
        "_run_gate",
        lambda events: ("NEUTRAL", "shadow_neutral", 0.0),
    )
    neutral = runner.run(request).require_match()
    assert neutral.registered_result.decision.signal == "NEUTRAL"
    assert neutral.registered_result.decision.option_side == "NO_TRADE"


def test_shadow_runner_refuses_runtime_connection(tmp_path):
    _, _, _, selection, recovery = build_runner(tmp_path)

    with pytest.raises(ShadowParityError, match="cannot connect"):
        OfflineShadowParityRunner(
            registry=build_phase3_registry(),
            selection=selection,
            recovery=recovery,
            runtime_connected=True,
        )


def test_shadow_runner_rejects_mismatched_recovery_selection(tmp_path):
    _, _, _, selection, recovery = build_runner(tmp_path)
    other_payload = selection.to_dict()
    other_payload["strategy_version"] = "9.9.9"
    other_payload.pop("selection_hash", None)
    other = StrategySelectionSnapshot.from_dict(other_payload)

    with pytest.raises(
        ShadowParityError,
        match="does not match",
    ):
        OfflineShadowParityRunner(
            registry=build_phase3_registry(),
            selection=other,
            recovery=recovery,
        )


def test_shadow_runner_detects_nondeterministic_legacy_output(
    tmp_path,
    monkeypatch,
):
    runner, request, _, _, _ = build_runner(tmp_path)
    calls = {"count": 0}

    def changing_gate(events):
        calls["count"] += 1
        if calls["count"] % 2:
            return "LONG", "changing_long", 200.0
        return "SHORT", "changing_short", -200.0

    monkeypatch.setattr(legacy_smc, "_run_gate", changing_gate)
    result = runner.run(request)

    assert result.status is ShadowParityStatus.MISMATCH
    assert any(
        "not deterministic" in reason
        for reason in result.mismatch_reasons
    )
    with pytest.raises(ShadowParityError, match="parity failed"):
        result.require_match()


def test_shadow_result_hash_is_deterministic(tmp_path, monkeypatch):
    runner, request, _, _, _ = build_runner(tmp_path)
    monkeypatch.setattr(
        legacy_smc,
        "_run_gate",
        lambda events: ("LONG", "stable", 200.0),
    )

    first = runner.run(request).require_match()
    second = runner.run(request).require_match()

    assert first.result_hash == second.result_hash
    assert first.to_dict() == second.to_dict()
