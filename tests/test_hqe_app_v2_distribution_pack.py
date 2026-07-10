from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_preflight_payload_locks_execution(monkeypatch, tmp_path):
    module = load("hqe_app_v2_preflight.py", "preflight_test")
    monkeypatch.setattr(module, "repo_root", lambda: REPO)
    monkeypatch.setattr(module, "check_internet", lambda timeout=2.0: True)

    payload = module.build_payload(tmp_path)

    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False


def test_release_pack_builder_creates_manifest(tmp_path):
    module = load("hqe_app_v2_release_pack_builder.py", "release_pack_test")
    payload = module.build_pack(
        tmp_path,
        r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
    )

    release_dir = Path(payload["release_dir"])
    assert payload["distribution_status"] == "PASS"
    assert (release_dir / "HQE_APP_V2_RELEASE_MANIFEST.json").exists()
    assert (release_dir / "START_HQE_APP_V2.cmd").exists()
    assert (release_dir / "README_FIRST.txt").exists()
    assert payload["real_orders_enabled"] is False


def test_release_manifest_has_hashes(tmp_path):
    module = load("hqe_app_v2_release_pack_builder.py", "release_pack_hash_test")
    payload = module.build_pack(
        tmp_path,
        r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
    )

    assert payload["file_count"] > 0
    assert all(item["sha256"] for item in payload["files"])
