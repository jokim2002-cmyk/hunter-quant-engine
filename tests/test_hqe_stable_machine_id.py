from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "scripts" / "hqe_product_license_common.py"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_machine_id_reuses_persisted_license_identity(monkeypatch, tmp_path):
    module = load_module("stable_machine_id_persisted")
    expected = "HQE-0123456789ABCDEF0123456789ABCDEF"
    stable = tmp_path / "HQE_STABLE_MACHINE_ID_V1.txt"
    stable.write_text(expected + "\n", encoding="utf-8")
    monkeypatch.setattr(module, "app_config_dir", lambda workspace=None: tmp_path)

    assert module.machine_id() == expected
    assert module.machine_id() == expected


def test_machine_id_is_created_once_and_remains_stable(monkeypatch, tmp_path):
    module = load_module("stable_machine_id_created")
    monkeypatch.setattr(module, "app_config_dir", lambda workspace=None: tmp_path)

    first = module.machine_id()
    second = module.machine_id()

    assert first == second
    assert re.fullmatch(r"HQE-[A-F0-9]{32}", first)
    assert (
        tmp_path / "HQE_STABLE_MACHINE_ID_V1.txt"
    ).read_text(encoding="utf-8").strip() == first


def test_invalid_stored_machine_id_is_repaired(monkeypatch, tmp_path):
    module = load_module("stable_machine_id_invalid")
    stable = tmp_path / "HQE_STABLE_MACHINE_ID_V1.txt"
    stable.write_text("INVALID\n", encoding="utf-8")
    monkeypatch.setattr(module, "app_config_dir", lambda workspace=None: tmp_path)

    repaired = module.machine_id()

    assert re.fullmatch(r"HQE-[A-F0-9]{32}", repaired)
    assert stable.read_text(encoding="utf-8").strip() == repaired
