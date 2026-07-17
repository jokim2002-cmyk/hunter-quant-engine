from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def source(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def test_windows_manifest_is_rc5_multi_strategy_release():
    manifest = json.loads(source("release/HQE_WINDOWS_RELEASE_MANIFEST.json"))
    assert manifest["product_version"] == "0.9.0-paper-rc5"
    assert manifest["release_channel"] == "PAPER_MULTI_STRATEGY_RC"


def test_windows_manifest_freezes_phase5_to_phase8_critical_assets():
    required = set(json.loads(source("release/HQE_WINDOWS_RELEASE_MANIFEST.json"))["required_files"])
    for relative in (
        "src/multi_strategy/product_ui_manager.py", "src/multi_strategy/import_workflow.py",
        "src/multi_strategy/parallel_observation.py",
        "release/HQE_MULTI_STRATEGY_PHASE8_RELEASE_CLOSURE.json",
    ):
        assert relative in required


def test_release_audit_requires_all_product_surfaces():
    text = source("scripts/hqe_release_candidate_audit.py")
    for marker in ("Product Strategy Manager", "Reviewed Package Import", "Parallel Observation Center"):
        assert marker in text


def test_release_audit_derives_freeze_version_from_release_manifest():
    text = source("scripts/hqe_release_candidate_audit.py")
    assert 'get("product_version", "")' in text
    assert "HQE_RELEASE_CANDIDATE_AUDIT_V2" in text


def test_preflight_allows_only_controlled_release_branches():
    text = source("scripts/hqe_release_workspace_preflight.py")
    assert '"master"' in text
    assert '"feature/hqe-multi-strategy-phase1"' in text
    assert "CONTROLLED_FEATURE_RELEASE" in text


def test_final_qa_covers_phase8_closure_and_visual_assets():
    text = source("scripts/hqe_final_release_qa.py")
    assert "HQE_MULTI_STRATEGY_PHASE8_RELEASE_CLOSURE.json" in text
    assert "hqe_multi_strategy_phase8_visual_acceptance.py" in text
    assert "hqe_multi_strategy_phase8_release_closure.py" in text


def test_visual_acceptance_executes_both_gui_render_smokes():
    app_text = source("scripts/hqe_product_app_v2.py")
    assert '"Product Strategy Manager",' in app_text
    assert '"Parallel Observation Center",' in app_text
    assert "open_parallel_observation_center_direct" in app_text
    assert "manager_button.invoke()" in app_text
    assert "observation_button.invoke()" in app_text
    assert "_hqe_wait_for_toplevel" in app_text
    assert "Parallel Isolated Paper Observation" in app_text
    assert "HQE_VISIBLE_NAV_TITLE_WAIT_RECOVERY_V2" in app_text
    assert "TITLE_FRAGMENT_WAIT_V3" in app_text
    assert "HQE_VISIBLE_NAV_CLEAN_EXIT_RECOVERY_V3" in app_text
    assert "SMOKE_FINALLY_DESTROY_V4" in app_text
    assert "HQE_DIRECT_PARALLEL_MANAGER_BUTTON_INVOKE_V7" in app_text
    assert "HQE_RECURSIVE_TOPLEVEL_DISCOVERY_V8" in app_text
    assert "def _hqe_all_toplevels" in app_text
    assert "walk(root)" in app_text
    assert "for child in _hqe_all_toplevels()" in app_text
    assert "before = set(_hqe_all_toplevels())" in app_text
    assert "find_visible_button" in app_text
    assert "observation_button.invoke()" in app_text
    assert "HQE_ALL_GUI_SMOKE_STARTUP_TIMERS_DISABLED_V7" in app_text
    assert "HQE_GUI_SMOKE_HEALTH_LOOP_DISABLED_V7" in app_text
    assert "HQE_GUI_SMOKE_REFRESH_ASYNC_NOOP_V9" in app_text
    assert "HQE_NORMAL_STARTUP_ORDER_RESTORED_V9" in app_text
    assert 'show_page("Overview")\n    refresh_status_async()' in app_text
    assert "root.after(15000, refresh_status_async)" in app_text
    assert "root.after(1200, lambda: refresh_daily_operations(False))" in app_text
    assert "root.after(1700, _deferred_fyers_startup)" in app_text
    assert "root.after(2400, lambda: refresh_broker_data_health(False))" in app_text
    assert "root.after(3100, lambda: refresh_market_data_center(False))" in app_text
    assert "HQE_SMOKE_CALLBACK_ERROR_CAPTURE_V6" in app_text
    assert "root.report_callback_exception" in app_text
    assert 'os.environ.get("HQE_FULL_CENTER_SMOKE") == "1"' in app_text
    assert "dialog.after_idle(open_parallel_observation_center)" not in app_text
    assert "HQE_DIRECT_PARALLEL_SYNCHRONOUS_OPEN_V5" not in app_text
    assert "HQE_ADVANCED_TOOLS_SMOKE_CLEAN_EXIT_V4" in app_text
    assert 'os.environ.get("HQE_ADVANCED_TOOLS_SMOKE") != "1"' in app_text
    assert "messagebox.askyesno = (" in app_text
    assert "root.quit()" in app_text
    assert "root.destroy()" in app_text
    assert "HQE_ADVANCED_TOOLS_DIRECT_NAV_PASS" in app_text
    text = source("scripts/hqe_multi_strategy_phase8_visual_acceptance.py")
    assert "HQE_ADVANCED_TOOLS_SMOKE" in text
    assert "HQE_ADVANCED_TOOLS_DIRECT_NAV_PASS" in text
    assert "HQE_FULL_CENTER_SMOKE" in text
    assert '"visible_navigation": {' in text
    assert '"actual_button_invocation"' in text
    assert "RECURSIVE_TOPLEVEL_DISCOVERY_V8" in text
    assert "MANAGER_VISIBLE_BUTTON_COMMAND" in text
    assert '"nested_toplevel_discovery": True' in text
    assert '"nested_observation_window_expected": True' in text
    assert "HQE_DIRECT_PARALLEL_MANAGER_BUTTON_INVOKE_V7" in text
    assert "HQE_ALL_GUI_SMOKE_STARTUP_TIMERS_DISABLED_V7" in text
    assert "HQE_GUI_SMOKE_HEALTH_LOOP_DISABLED_V7" in text
    assert "HQE_SMOKE_CALLBACK_ERROR_CAPTURE_V6" in text
    assert "HQE_ADVANCED_TOOLS_SMOKE_CLEAN_EXIT_V4" in text
    assert '"smoke_background_worker_started": False' in text
    assert '"smoke_clean_exit_marker_found"' in text
    assert "Parallel Isolated Paper Observation" in text
    assert '"screenshots_captured": False' in text


def test_phase8_closure_has_no_runtime_or_execution_call_surface():
    text = source("scripts/hqe_multi_strategy_phase8_release_closure.py")
    forbidden = ("place_order(", "submit_order(", "write_human_gate(", "start_watch(", "prepare_canonical_runtime_cutover(")
    assert not any(token in text for token in forbidden)
