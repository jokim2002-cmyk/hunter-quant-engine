from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QA = REPO / "scripts" / "hqe_final_release_qa.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hqe_final_release_qa", QA)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_required_release_assets_cover_core_product_files():
    module = load_module()
    required = set(module.REQUIRED_RELEASE_ASSETS)
    assert "scripts/hqe_product_app_v2.py" in required
    assert "release/HQE_PAPER_ONLY_RC_FREEZE_MANIFEST.json" in required
    assert "release/HQE_PAPER_ONLY_RC_SIGNOFF.json" in required
    assert "assets/HQE_PRODUCT_APP.ico" in required


def test_final_release_qa_passes(tmp_path):
    module = load_module()
    payload = module.build_final_release_qa(REPO, tmp_path)
    assert payload["status"] == "PASS"
    assert payload["real_order_invoked"] is False
    assert payload["broker_execution_invoked"] is False
    assert payload["auto_trading_invoked"] is False
    assert Path(payload["report_path"]).exists()
