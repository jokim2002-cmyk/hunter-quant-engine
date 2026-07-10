from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_strategy_builder_engine.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_builder_generates_valid_paper_only_pack():
    module = load("strategy_builder_valid")
    form = module.builder_defaults("breakout")
    pack = module.build_strategy_pack(form)
    preview = module.strategy_preview(pack)

    assert preview["valid"] is True
    assert preview["paper_compatible"] is True
    assert pack["status"] == "draft"
    assert pack["instruments"][0]["direction"] == "buy_only"
    assert pack["safety"]["no_option_selling"] is True
    assert pack["safety"]["no_real_orders"] is True


def test_builder_rejects_invalid_ltp_range():
    module = load("strategy_builder_range")
    form = module.builder_defaults("momentum_trend")
    form["ltp_min"] = 200
    form["ltp_max"] = 20
    try:
        module.build_strategy_pack(form)
    except ValueError as exc:
        assert "ltp_max" in str(exc)
    else:
        raise AssertionError("Invalid LTP range must be rejected.")


def test_builder_rejects_option_selling_side():
    module = load("strategy_builder_side")
    form = module.builder_defaults("reversal")
    form["option_sides"] = "CE,SELL"
    try:
        module.build_strategy_pack(form)
    except ValueError as exc:
        assert "CE and/or PE" in str(exc)
    else:
        raise AssertionError("Option selling side must be rejected.")


def test_save_and_select_paper_pack(tmp_path):
    module = load("strategy_builder_selection")
    workspace = tmp_path / "workspace"
    form = module.builder_defaults("scalping")
    form["strategy_id"] = "my_scalping_test"
    path = module.save_draft(form, workspace)
    assert path.exists()

    selection_path = module.select_active_paper_pack(path, workspace)
    payload = json.loads(selection_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "PAPER_ONLY"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False

    snapshot = module.active_selection_snapshot(workspace)
    assert snapshot["selected"] is True
    assert snapshot["available"] is True
    assert snapshot["strategy_id"] == "my_scalping_test"

    assert module.clear_active_selection(workspace) is True
    assert module.active_selection_snapshot(workspace)["selected"] is False


def test_preview_warns_when_target_not_above_stop():
    module = load("strategy_builder_warning")
    form = module.builder_defaults("breakout")
    form["stop_loss_percent"] = 1.2
    form["target_percent"] = 0.4
    pack = module.build_strategy_pack(form)
    preview = module.strategy_preview(pack)
    assert any("Target percent" in item for item in preview["warnings"])


def test_builder_guard_locks_execution():
    module = load("strategy_builder_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["selection_mode"] == "PAPER_ONLY"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False
