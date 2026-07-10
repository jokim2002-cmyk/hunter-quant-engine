from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_release_readiness_engine.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_backup_and_restore_staging_do_not_overwrite(tmp_path):
    module = load("release_backup_restore")
    workspace = tmp_path / "workspace"
    strategy = (
        workspace
        / "strategy_packs"
        / "drafts"
        / "sample.json"
    )
    strategy.parent.mkdir(parents=True)
    strategy.write_text('{"sample": true}', encoding="utf-8")
    selection = workspace / "HQE_ACTIVE_STRATEGY_SELECTION.json"
    selection.write_text('{"strategy_id": "sample"}', encoding="utf-8")

    backup = module.create_backup(REPO, workspace)
    assert backup["status"] == "PASS"
    assert Path(backup["backup_path"]).exists()

    original = strategy.read_text(encoding="utf-8")
    restore = module.stage_restore(
        REPO,
        workspace,
        Path(backup["backup_path"]),
    )
    assert restore["status"] == "PASS"
    assert restore["overwrite_performed"] is False
    assert Path(restore["staging_dir"]).exists()
    assert strategy.read_text(encoding="utf-8") == original


def test_restore_blocks_zip_path_traversal(tmp_path):
    module = load("release_restore_traversal")
    source = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("../escape.txt", "unsafe")
        archive.writestr(
            "HQE_BACKUP_MANIFEST.json",
            json.dumps({"version": "x"}),
        )

    try:
        module.stage_restore(
            REPO,
            tmp_path / "workspace",
            source,
        )
    except ValueError as exc:
        assert "Unsafe ZIP paths" in str(exc)
    else:
        raise AssertionError("Unsafe backup ZIP must be rejected.")


def test_required_manifest_files_exist():
    module = load("release_manifest")
    manifest = module.release_manifest(REPO)
    checks = module.check_required_files(REPO, manifest)
    assert checks
    assert all(
        item["status"] == "PASS"
        for item in checks
    )


def test_shortcut_command_uses_powershell_installer():
    module = load("release_shortcut")
    command = module.install_shortcut_command(REPO)
    joined = " ".join(command).lower()
    assert "powershell.exe" in joined
    assert "hqe_install_desktop_shortcut.ps1" in joined
    assert "--real" not in joined


def test_release_guard_locks_execution():
    module = load("release_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["dry_run_only"] is True
    assert payload["backup_restore_policy"] == (
        "RESTORE_STAGING_ONLY_NO_OVERWRITE"
    )
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
