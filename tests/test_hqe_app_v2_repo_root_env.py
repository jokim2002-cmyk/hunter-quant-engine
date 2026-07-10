from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def load_module(name: str):
    scripts_dir = str(APP.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    spec = importlib.util.spec_from_file_location(name, APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_repo_root_honors_env_hint(monkeypatch, tmp_path):
    module = load_module("hqe_product_app_v2_repo_root_env_test")
    monkeypatch.setenv("HQE_REPO_HINT", str(tmp_path))

    assert module.repo_root() == tmp_path


def test_repo_root_falls_back_to_script_parent(monkeypatch):
    module = load_module("hqe_product_app_v2_repo_root_fallback_test")
    monkeypatch.delenv("HQE_REPO_HINT", raising=False)

    assert module.repo_root() == APP.resolve().parents[1]
