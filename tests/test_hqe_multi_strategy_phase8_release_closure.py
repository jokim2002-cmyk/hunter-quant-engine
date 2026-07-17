from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_multi_strategy_phase8_release_closure.py"


def load_module():
    spec = importlib.util.spec_from_file_location("phase8_closure", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "release").mkdir(parents=True)
    (repo / "release" / "HQE_WINDOWS_RELEASE_MANIFEST.json").write_text(
        json.dumps({"product_version": "0.9.0-paper-rc5"}), encoding="utf-8"
    )
    return repo


def make_visual(tmp_path: Path, status: str = "PASS") -> Path:
    path = tmp_path / "visual.json"
    path.write_text(json.dumps({"status": status, "actual_gui_render_smoke_executed": True}), encoding="utf-8")
    return path


def final_payload(module, repo, visual):
    return module.build_final_payload(
        repo, visual, source_head="abc123", focused="30/30 PASS",
        cumulative="428/428 PASS", environment="9/9 PASS",
        full_regression="3586/3586 PASS", freeze_verification="PASS",
    )


def test_guard_payload_permanently_locks_execution():
    module = load_module(); payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["canonical_activation_allowed"] is False
    assert payload["real_orders_allowed"] is False
    assert payload["safety_lock"]["no_fake_trades"] is True


def test_release_version_comes_from_windows_manifest(tmp_path):
    module = load_module(); repo = make_repo(tmp_path)
    assert module.release_version(repo) == "0.9.0-paper-rc5"


def test_final_payload_requires_visual_pass(tmp_path):
    module = load_module(); repo = make_repo(tmp_path); visual = make_visual(tmp_path, "FAILED")
    try: final_payload(module, repo, visual)
    except ValueError: pass
    else: raise AssertionError("visual failure must block closure")


def test_final_payload_requires_every_validation_pass(tmp_path):
    module = load_module(); repo = make_repo(tmp_path); visual = make_visual(tmp_path)
    try:
        module.build_final_payload(repo, visual, source_head="abc", focused="FAILED", cumulative="PASS", environment="PASS", full_regression="PASS", freeze_verification="PASS")
    except ValueError: pass
    else: raise AssertionError("validation failure must block closure")


def test_final_payload_records_all_closed_phases(tmp_path):
    module = load_module(); repo = make_repo(tmp_path); payload = final_payload(module, repo, make_visual(tmp_path))
    assert payload["multi_strategy_phases_closed"] == list(range(9))


def test_final_payload_records_source_head(tmp_path):
    module = load_module(); repo = make_repo(tmp_path); payload = final_payload(module, repo, make_visual(tmp_path))
    assert payload["source_head_before_closure_commit"] == "abc123"


def test_final_payload_has_no_execution_authority(tmp_path):
    module = load_module(); repo = make_repo(tmp_path); payload = final_payload(module, repo, make_visual(tmp_path))
    assert payload["real_orders_enabled"] is False
    assert payload["canonical_activation_performed"] is False
    assert payload["master_merge_performed"] is False
    assert payload["safety_lock"]["no_fake_trades"] is True


def test_atomic_write_leaves_no_temporary_file(tmp_path):
    module = load_module(); target = tmp_path / "x.json"
    module.atomic_write_json(target, {"ok": True})
    assert json.loads(target.read_text()) == {"ok": True}
    assert not target.with_suffix(".json.tmp").exists()


def test_write_and_verify_final_closure(tmp_path):
    module = load_module(); repo = make_repo(tmp_path); visual = make_visual(tmp_path)
    ready = module.write_ready_closure(repo, visual, source_head="ready")
    assert ready["closure_status"] == module.READY_STATUS
    assert module.verify_closure(repo, require_final=False)["status"] == "PASS"
    assert module.verify_closure(repo, require_final=True)["status"] == "FAILED"
    written = module.write_final_closure(repo, visual, source_head="abc", focused="PASS", cumulative="PASS", environment="PASS", full_regression="PASS", freeze_verification="PASS")
    assert written["closure_status"] == module.FINAL_STATUS
    assert module.verify_closure(repo)["status"] == "PASS"


def test_visual_evidence_tamper_is_detected(tmp_path):
    module = load_module(); repo = make_repo(tmp_path); visual = make_visual(tmp_path)
    module.write_final_closure(repo, visual, source_head="abc", focused="PASS", cumulative="PASS", environment="PASS", full_regression="PASS", freeze_verification="PASS")
    visual.write_text('{"status":"CHANGED"}', encoding="utf-8")
    assert module.verify_closure(repo)["status"] == "FAILED"


def test_unsafe_closure_flag_is_rejected(tmp_path):
    module = load_module(); repo = make_repo(tmp_path); visual = make_visual(tmp_path)
    module.write_final_closure(repo, visual, source_head="abc", focused="PASS", cumulative="PASS", environment="PASS", full_regression="PASS", freeze_verification="PASS")
    path = repo / module.CLOSURE_PATH; payload = json.loads(path.read_text()); payload["real_orders_enabled"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert module.verify_closure(repo)["status"] == "FAILED"


def test_missing_closure_fails_verification(tmp_path):
    module = load_module(); repo = make_repo(tmp_path)
    assert module.verify_closure(repo)["status"] == "FAILED"
