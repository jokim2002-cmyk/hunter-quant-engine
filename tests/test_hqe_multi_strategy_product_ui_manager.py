from __future__ import annotations

from src.multi_strategy.product_ui_manager import (
    build_product_strategy_manager_snapshot,
    evaluate_clear_configuration,
    evaluate_configuration_selection,
    guard_payload,
)


def snapshots(*, running=False, lifecycle="FLAT"):
    pack = {
        "packs": [
            {
                "strategy_id": "hqe_current_smc_compatibility",
                "name": "Current SMC Compatibility",
                "version": "1.0.0",
                "source": "builtin",
                "path": "C:/packs/current_smc.json",
                "valid": True,
                "status": "VALID",
                "payload": {
                    "description": "Reviewed current strategy",
                    "parameters": {"timeframe": "5m"},
                    "safety": {"paper_only": True},
                    "validation": {"reviewed": True},
                },
            },
            {
                "strategy_id": "draft_breakout",
                "name": "Draft Breakout",
                "version": "0.1.0",
                "source": "draft",
                "path": "C:/packs/draft.json",
                "valid": True,
                "status": "VALID",
                "payload": {
                    "parameters": {"period": 20},
                    "safety": {"paper_only": True},
                },
            },
        ]
    }
    builder = {
        "selection": {
            "strategy_id": "draft_breakout",
            "strategy_version": "0.1.0",
            "path": "C:/packs/draft.json",
            "display_text": "Active paper strategy: Draft Breakout",
        }
    }
    runtime = {
        "strategy_id": "hqe_current_smc_compatibility",
        "strategy_version": "1.0.0",
        "multi_strategy_runtime_mode": "LEGACY_COMPATIBILITY",
        "multi_strategy_gate_status": "MISSING",
        "multi_strategy_lifecycle": lifecycle,
        "multi_strategy_namespace": "C:/runtime",
    }
    paper = {"position": {"status": lifecycle}}
    return pack, builder, runtime, paper, running


def build(*, running=False, lifecycle="FLAT"):
    pack, builder, runtime, paper, running = snapshots(
        running=running,
        lifecycle=lifecycle,
    )
    return build_product_strategy_manager_snapshot(
        pack_snapshot=pack,
        builder_snapshot=builder,
        runtime_snapshot=runtime,
        paper_snapshot=paper,
        runtime_running=running,
    )


def test_snapshot_lists_strategies_and_runtime_truth():
    snapshot = build()
    assert snapshot["status"] == "PASS"
    assert snapshot["available_count"] == 2
    assert snapshot["valid_count"] == 2
    assert snapshot["records"][0]["reviewed_current_smc"] is True
    assert snapshot["selected_configuration"]["strategy_id"] == "draft_breakout"
    assert snapshot["canonical_runtime"]["runtime_mode"] == "LEGACY_COMPATIBILITY"
    assert snapshot["selection_change_allowed"] is True
    assert snapshot["canonical_activation_allowed"] is False
    assert snapshot["human_gate_creation_allowed"] is False
    assert snapshot["real_orders_allowed"] is False


def test_selection_allowed_only_as_configuration():
    snapshot = build()
    decision = evaluate_configuration_selection(snapshot, snapshot["records"][1])
    assert decision.allowed is True
    assert decision.configuration_only is True
    assert decision.canonical_activation_allowed is False
    assert decision.human_gate_creation_allowed is False
    assert decision.real_orders_allowed is False


def test_runtime_running_blocks_selection_and_clear():
    snapshot = build(running=True)
    selected = evaluate_configuration_selection(snapshot, snapshot["records"][0])
    cleared = evaluate_clear_configuration(snapshot)
    assert selected.allowed is False
    assert cleared.allowed is False
    assert "Paper runtime is running" in selected.blockers


def test_open_and_held_positions_block_changes():
    for lifecycle in ("OPEN", "HELD"):
        snapshot = build(lifecycle=lifecycle)
        decision = evaluate_configuration_selection(snapshot, snapshot["records"][0])
        assert decision.allowed is False
        assert any(lifecycle in blocker for blocker in decision.blockers)


def test_invalid_or_non_paper_pack_is_blocked():
    snapshot = build()
    record = dict(snapshot["records"][0])
    record["valid"] = False
    record["paper_only"] = False
    decision = evaluate_configuration_selection(snapshot, record)
    assert decision.allowed is False
    assert "Strategy pack validation has not passed" in decision.blockers
    assert "Strategy pack is not paper-only" in decision.blockers


def test_guard_has_zero_execution_authority():
    guard = guard_payload()
    assert guard["guard_check_status"] == "PASS"
    assert guard["configuration_selection_only"] is True
    assert guard["canonical_activation_allowed"] is False
    assert guard["runtime_control_allowed"] is False
    assert guard["lifecycle_write_allowed"] is False
    assert guard["real_orders_allowed"] is False
    assert guard["broker_execution_allowed"] is False
    assert guard["real_money_allowed"] is False
