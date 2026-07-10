from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_release_candidate_audit.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_app_navigation_and_ast_safety_pass():
    module = load("rc_navigation_safety")
    navigation = module.app_navigation_check(REPO)
    safety = module.unsafe_app_call_check(REPO)
    assert navigation["status"] == "PASS", navigation
    assert safety["status"] == "PASS", safety


def test_workspace_write_check_is_non_destructive(tmp_path):
    module = load("rc_workspace")
    workspace = tmp_path / "workspace"
    result = module.workspace_write_check(workspace)
    assert result["status"] == "PASS"
    assert list(workspace.iterdir()) == []


def test_freeze_manifest_generation_and_verification(tmp_path):
    module = load("rc_freeze")
    repo = tmp_path / "repo"
    release = repo / "release"
    scripts = repo / "scripts"
    release.mkdir(parents=True)
    scripts.mkdir(parents=True)
    app = scripts / "app.py"
    app.write_text("print('paper only')\n", encoding="utf-8")
    manifest = {
        "required_files": ["scripts/app.py"],
        "guard_scripts": [],
    }
    (release / "HQE_WINDOWS_RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    generated = module.generate_freeze_manifest(
        repo,
        source_head="abc1234",
    )
    assert generated["file_count"] == 1
    verified = module.verify_freeze_manifest(repo)
    assert verified["status"] == "PASS"

    app.write_text("print('changed')\n", encoding="utf-8")
    changed = module.verify_freeze_manifest(repo)
    assert changed["status"] == "FAILED"
    assert "scripts/app.py" in changed["mismatches"]


def test_launcher_assets_and_freeze_manifest_pass():
    module = load("rc_launcher_freeze")
    launcher = module.launcher_check(REPO)
    freeze = module.verify_freeze_manifest(REPO)
    assert launcher["status"] == "PASS", launcher
    assert freeze["status"] == "PASS", freeze


def test_guard_payload_locks_execution():
    module = load("rc_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["snapshot_mode"] == "READ_ONLY"
    assert payload["freeze_hashes"] == "SHA256"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["option_selling_enabled"] is False
