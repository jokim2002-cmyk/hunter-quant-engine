from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_strategy_pack_schema.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_all_builtin_strategy_packs_validate():
    module = load("strategy_schema_builtins")
    packs = module.builtin_strategy_packs()
    assert len(packs) == 7
    for pack in packs:
        result = module.validate_strategy_pack(pack)
        assert result["valid"], result["errors"]


def test_locked_candidate_matches_current_forward_constraints():
    module = load("strategy_schema_locked")
    locked = next(
        pack
        for pack in module.builtin_strategy_packs()
        if pack["strategy_id"] == "hqe_locked_forward_candidate"
    )
    assert locked["status"] == "locked_validation"
    assert locked["validation"]["locked_candidate"] is True
    assert locked["instruments"][0]["option_sides"] == ["PE"]
    assert locked["rules"]["filters"][0]["value"] == 1


def test_option_selling_is_rejected():
    module = load("strategy_schema_selling")
    pack = copy.deepcopy(module.builtin_strategy_packs()[0])
    pack["instruments"][0]["direction"] = "sell_only"
    result = module.validate_strategy_pack(pack)
    assert result["valid"] is False
    assert any("selling" in error for error in result["errors"])


def test_versioning_and_fingerprint_are_stable():
    module = load("strategy_schema_version")
    pack = module.builtin_strategy_packs()[0]
    first = module.pack_fingerprint(pack)
    second = module.pack_fingerprint(copy.deepcopy(pack))
    assert first == second
    assert module.bump_patch_version("1.2.9") == "1.2.10"


def test_schema_guard_locks_execution():
    module = load("strategy_schema_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["option_selling_enabled"] is False
