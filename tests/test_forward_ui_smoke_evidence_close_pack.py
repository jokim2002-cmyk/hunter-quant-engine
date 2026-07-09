import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_forward_ui_smoke_evidence_close_pack.py"
SPEC = importlib.util.spec_from_file_location("build_forward_ui_smoke_evidence_close_pack", SCRIPT_PATH)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def create_artifacts(root: Path) -> None:
    final = root / "final"
    operator = root / "operator"
    history = root / "history"
    dashboard = root / "dashboard"
    daily = root / "daily"
    for folder in (final, operator, history, dashboard, daily):
        folder.mkdir(parents=True, exist_ok=True)

    (final / "MODULE_138_FINAL_LAUNCH_PACK.html").write_text(
        "<html><h1>HQE Dashboard Final Launch Pack</h1><h2>Safety Lock</h2><p>This is not a profitability claim.</p></html>",
        encoding="utf-8",
    )

    (operator / "MODULE_137_OPERATOR_CONSOLE.html").write_text(
        "<html><h1>HQE Forward Paper Operator Console</h1><h2>Safety Lock</h2><p>This is not a profitability claim.</p></html>",
        encoding="utf-8",
    )
    write_json(operator / "MODULE_137_OPERATOR_CONSOLE_MODEL.json", {
        "operator_status": "OPEN_PAPER_POSITION_MONITOR",
        "latest_day_label": "DRY_RUN_001",
        "latest_event": "POSITION_OPENED",
        "latest_action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
        "latest_position_state": "OPEN",
    })

    (history / "MODULE_136_DASHBOARD_HISTORY_INDEX.html").write_text(
        "<html><h1>HQE Forward Paper History Index</h1><p>Paper/simulation only. This is not a profitability claim.</p></html>",
        encoding="utf-8",
    )
    write_json(history / "MODULE_136_DASHBOARD_HISTORY_INDEX_MODEL.json", {
        "history_status": "HISTORY_READY",
        "total_records": 2,
    })

    (dashboard / "MODULE_134_FORWARD_PAPER_DASHBOARD.html").write_text(
        "<html><h1>Safety</h1><p>Paper dashboard. This is not a profitability claim.</p></html>",
        encoding="utf-8",
    )

    write_json(daily / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json", {
        "day_label": "DRY_RUN_001",
        "event": "POSITION_OPENED",
        "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
        "position_state": "OPEN",
    })


def test_safety_contract():
    assert mod.PAPER_ONLY is True
    assert mod.READ_ONLY_CLOSE_PACK is True
    assert mod.LOCAL_STATIC_HTML_ONLY is True
    assert mod.BROKER_EXECUTION_ALLOWED is False
    assert mod.REAL_ORDERS_ALLOWED is False
    assert mod.REAL_MONEY_ALLOWED is False
    assert mod.AUTO_TRADING_ALLOWED is False
    assert mod.OPTION_SELLING_ALLOWED is False
    assert mod.EXTERNAL_API_ALLOWED is False
    assert mod.PROFITABILITY_CLAIM is False
    mod.assert_safety_contract()


def test_smoke_pass_model(tmp_path):
    create_artifacts(tmp_path)
    model = mod.build_smoke_model(mod.SmokeInputs(runs_root=tmp_path, out_dir=tmp_path / "out"))
    assert model["module"] == 139
    assert model["smoke_status"] == "UI_SMOKE_PASS_CLOSE_PACK_READY"
    assert model["close_decision"] == "CLOSE_PACK_READY_PAPER_ONLY"
    assert model["present_artifacts"] == 7
    assert model["missing_artifacts"] == []
    assert model["failed_html_checks"] == []
    assert model["operator_status"] == "OPEN_PAPER_POSITION_MONITOR"
    assert model["latest_day_label"] == "DRY_RUN_001"


def test_missing_artifacts_review_required(tmp_path):
    model = mod.build_smoke_model(mod.SmokeInputs(runs_root=tmp_path / "empty", out_dir=tmp_path / "out"))
    assert model["smoke_status"] == "UI_SMOKE_REVIEW_REQUIRED"
    assert model["close_decision"] == "REVIEW_REQUIRED_PAPER_ONLY"
    assert model["present_artifacts"] == 0
    assert len(model["missing_artifacts"]) > 0


def test_write_close_pack_files(tmp_path):
    create_artifacts(tmp_path)
    model = mod.build_smoke_model(mod.SmokeInputs(runs_root=tmp_path, out_dir=tmp_path / "out"))
    files = mod.write_close_pack_files(tmp_path / "out", model)
    assert Path(files["close_pack_model_json"]).exists()
    assert Path(files["close_pack_report_md"]).exists()
    assert Path(files["close_pack_summary_csv"]).exists()
    assert Path(files["close_pack_html"]).exists()
    assert Path(files["open_close_pack_bat"]).exists()
    html = Path(files["close_pack_html"]).read_text(encoding="utf-8")
    assert "HQE UI Smoke Evidence Close Pack" in html
    assert "Safety Lock" in html
    assert "not a profitability claim" in html.lower()


def test_html_escaping(tmp_path):
    create_artifacts(tmp_path)
    model = mod.build_smoke_model(mod.SmokeInputs(runs_root=tmp_path, out_dir=tmp_path / "out"))
    model["latest_day_label"] = "<script>alert(1)</script>"
    html = mod.render_close_pack_html(model)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
