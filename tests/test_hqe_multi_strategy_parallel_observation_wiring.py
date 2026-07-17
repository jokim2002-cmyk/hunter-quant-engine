from __future__ import annotations

import ast
from pathlib import Path

from src.multi_strategy.product_ui_manager import (
    build_product_strategy_manager_snapshot,
    guard_payload as product_manager_guard,
)

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "scripts" / "hqe_product_app_v2.py"
MODULE = ROOT / "src" / "multi_strategy" / "parallel_observation.py"
REHEARSAL = (
    ROOT
    / "scripts"
    / "hqe_multi_strategy_phase7_parallel_observation_rehearsal.py"
)


def app_source() -> str:
    return APP.read_text(encoding="utf-8")


def test_product_app_imports_phase7_after_repo_bootstrap():
    text = app_source()
    bootstrap = "REPO_ROOT = Path(__file__).resolve().parents[1]"
    observation_import = "from src.multi_strategy.parallel_observation import ("
    assert bootstrap in text
    assert observation_import in text
    assert text.index(bootstrap) < text.index(observation_import)
    for name in (
        "ObservationLaneConfig",
        "create_parallel_observation_session",
        "run_parallel_observation_cycle",
        "close_parallel_observation_session",
        "eligible_parallel_observation_strategies",
        "parallel_observation_snapshot",
        "load_recorded_input_from_csv",
        "guard_payload as parallel_observation_guard_payload",
    ):
        assert name in text


def test_product_app_guard_exposes_phase7_observation_safety():
    text = app_source()
    assert '"multi_strategy_phase7_parallel_observation":' in text
    assert "parallel_observation_guard_payload()" in text


def test_product_manager_refresh_includes_observation_snapshot():
    text = app_source()
    assert "observation_snapshot = parallel_observation_snapshot(workspace)" in text
    assert "observation_snapshot=observation_snapshot" in text
    assert "Parallel observation:" in text


def test_visible_parallel_observation_center_and_controls_exist():
    text = app_source()
    for phrase in (
        "def open_parallel_observation_center()",
        "Parallel Isolated Paper Observation",
        "Create Isolated Session",
        "Run Recorded Observation Cycle",
        "Close Flat Session",
        "Open Evidence Folder",
        "OBSERVATION ONLY • PER-LANE STATE/LEDGER/P&L",
    ):
        assert phrase in text


def test_parallel_center_has_no_canonical_activation_or_runtime_calls():
    tree = ast.parse(app_source())
    center = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "open_parallel_observation_center"
    )
    call_names = {
        node.func.id
        for node in ast.walk(center)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert {
        "create_parallel_observation_session",
        "run_parallel_observation_cycle",
        "close_parallel_observation_session",
    }.issubset(call_names)
    for forbidden in (
        "select_paper_pack",
        "clear_paper_selection",
        "prepare_canonical_runtime_cutover",
        "write_human_gate",
        "start_watch",
        "stop_watch",
        "send_order",
        "place_order",
    ):
        assert forbidden not in call_names


def test_rehearsal_bootstraps_repo_before_phase7_import():
    text = REHEARSAL.read_text(encoding="utf-8")
    bootstrap = "REPO_ROOT = Path(__file__).resolve().parents[1]"
    module_import = "from src.multi_strategy.parallel_observation import ("
    assert bootstrap in text
    assert "sys.path.insert(0, str(REPO_ROOT))" in text
    assert text.index(bootstrap) < text.index(module_import)


def test_parallel_observation_module_never_imports_canonical_runtime():
    text = MODULE.read_text(encoding="utf-8")
    assert "canonical_runtime" not in {
        alias.name
        for node in ast.walk(ast.parse(text))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    for forbidden in (
        "MODULE_131_POSITION_STATE",
        "MODULE_131_PAPER_LEDGER",
        "prepare_canonical_runtime_cutover",
        "HQE_MULTI_STRATEGY_ACTIVE_SELECTION",
    ):
        assert forbidden not in text


def test_product_manager_snapshot_surfaces_observation_without_authority():
    snapshot = build_product_strategy_manager_snapshot(
        pack_snapshot={"packs": []},
        builder_snapshot={"selection": {}},
        runtime_snapshot={},
        paper_snapshot={"position": {"status": "FLAT"}},
        runtime_running=False,
        observation_snapshot={
            "status": "PASS",
            "session_count": 2,
            "active_session_count": 1,
            "latest_session_id": "parallel-one",
            "observation_root": "C:/isolated",
            "operator_message": "one active isolated session",
            "selected_session": {
                "status": "ACTIVE",
                "cycle_count": 4,
                "lane_count": 2,
                "active_position_count": 1,
            },
        },
    )
    observation = snapshot["parallel_observation"]
    assert observation["session_count"] == 2
    assert observation["active_session_count"] == 1
    assert observation["latest_session_id"] == "parallel-one"
    assert observation["latest_cycle_count"] == 4
    assert observation["latest_lane_count"] == 2
    assert observation["canonical_runtime_connected"] is False
    assert observation["canonical_selection_allowed"] is False
    assert observation["canonical_activation_allowed"] is False
    assert observation["real_orders_allowed"] is False


def test_product_manager_guard_advertises_isolated_observation_boundary():
    guard = product_manager_guard()
    assert guard["parallel_observation_display"] is True
    assert guard["parallel_observation_canonical_connection_blocked"] is True
    assert guard["parallel_isolated_observation_allowed"] is True
    assert guard["canonical_activation_allowed"] is False
    assert guard["real_orders_allowed"] is False
