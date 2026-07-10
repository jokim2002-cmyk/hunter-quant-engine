from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_strategy_pack_registry.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_registry_discovers_builtin_packs(tmp_path):
    module = load("strategy_registry_discovery")
    repo = tmp_path / "repo"
    builtin = repo / "strategy_packs" / "builtin"
    builtin.mkdir(parents=True)
    source = REPO / "strategy_packs" / "builtin"
    for path in source.glob("*.json"):
        shutil.copy2(path, builtin / path.name)

    snapshot = module.registry_snapshot(repo, tmp_path / "workspace")
    assert snapshot["pack_count"] == 7
    assert snapshot["valid_count"] == 7
    assert snapshot["locked_count"] == 1


def test_import_export_and_clone_are_json_only(tmp_path):
    module = load("strategy_registry_io")
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    source = (
        REPO
        / "strategy_packs"
        / "builtin"
        / "hqe_breakout_option_buy.json"
    )

    imported = module.import_strategy_pack(
        source,
        repo,
        workspace,
    )
    assert imported.suffix == ".json"
    assert imported.exists()

    exported = module.export_strategy_pack(
        imported,
        repo,
        workspace,
    )
    assert exported.suffix == ".json"
    assert exported.exists()

    cloned = module.clone_pack_as_draft(
        imported,
        repo,
        workspace,
        new_strategy_id="my_breakout_draft",
        new_name="My Breakout Draft",
    )
    payload = json.loads(cloned.read_text(encoding="utf-8"))
    assert payload["status"] == "draft"
    assert payload["strategy_id"] == "my_breakout_draft"
    assert payload["validation"]["locked_candidate"] is False


def test_registry_guard_locks_execution():
    module = load("strategy_registry_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["json_only"] is True
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
