from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_release_workspace_preflight.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hqe_release_workspace_preflight", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_known_temp_artifact_list_covers_current_cleanup_targets():
    module = load_module()
    targets = set(module.KNOWN_TEMP_ARTIFACTS)
    assert "HQE.spec" in targets
    assert "build" in targets
    assert "profile.stats" in targets
    assert "scripts/hqe_product_app_v2_backup.py" in targets


def test_release_workspace_preflight_passes():
    module = load_module()
    payload = module.workspace_preflight(REPO)
    assert payload["status"] == "PASS"
    assert payload["branch"] in module.APPROVED_RELEASE_BRANCHES
    assert payload["branch_allowed"] is True
    assert payload["release_mode"] in {"MASTER_RELEASE", "CONTROLLED_FEATURE_RELEASE"}
    assert payload["remaining_temp_artifacts"] == []
    assert payload["unexpected_git_changes"] == []
    assert payload["real_order_invoked"] is False
    assert payload["broker_execution_invoked"] is False
    assert payload["canonical_activation_invoked"] is False
    assert payload["master_merge_invoked"] is False
