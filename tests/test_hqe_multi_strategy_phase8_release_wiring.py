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
    text = source("scripts/hqe_multi_strategy_phase8_visual_acceptance.py")
    assert "HQE_ADVANCED_TOOLS_SMOKE" in text
    assert "HQE_FULL_CENTER_SMOKE" in text
    assert '"screenshots_captured": False' in text


def test_phase8_closure_has_no_runtime_or_execution_call_surface():
    text = source("scripts/hqe_multi_strategy_phase8_release_closure.py")
    forbidden = ("place_order(", "submit_order(", "write_human_gate(", "start_watch(", "prepare_canonical_runtime_cutover(")
    assert not any(token in text for token in forbidden)
