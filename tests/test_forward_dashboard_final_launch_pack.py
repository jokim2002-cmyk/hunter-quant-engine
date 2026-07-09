import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_forward_dashboard_final_launch_pack.py"
SPEC = importlib.util.spec_from_file_location("build_forward_dashboard_final_launch_pack", SCRIPT_PATH)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def create_artifacts(root: Path) -> None:
    operator = root / "operator"
    history = root / "history"
    dashboard = root / "dashboard"
    daily = root / "daily"
    for folder in (operator, history, dashboard, daily):
        folder.mkdir(parents=True, exist_ok=True)

    (operator / "MODULE_137_OPERATOR_CONSOLE.html").write_text("<html>operator</html>", encoding="utf-8")
    write_json(operator / "MODULE_137_OPERATOR_CONSOLE_MODEL.json", {
        "operator_status": "OPEN_PAPER_POSITION_MONITOR",
        "operator_message": "Open paper position monitor karo.",
        "latest_day_label": "DRY_RUN_001",
        "latest_event": "POSITION_OPENED",
        "latest_action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
        "latest_position_state": "OPEN",
    })

    (history / "MODULE_136_DASHBOARD_HISTORY_INDEX.html").write_text("<html>history</html>", encoding="utf-8")
    write_json(history / "MODULE_136_DASHBOARD_HISTORY_INDEX_MODEL.json", {
        "history_status": "HISTORY_READY",
        "total_records": 2,
    })

    (dashboard / "MODULE_134_FORWARD_PAPER_DASHBOARD.html").write_text("<html>dashboard</html>", encoding="utf-8")
    (daily / "MODULE_133_DAILY_PAPER_TRADING_REPORT.md").write_text("# Daily report", encoding="utf-8")
    write_json(daily / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json", {
        "day_label": "DRY_RUN_001",
        "event": "POSITION_OPENED",
        "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
        "position_state": "OPEN",
    })


def test_safety_contract():
    assert mod.PAPER_ONLY is True
    assert mod.READ_ONLY_LAUNCH_PACK is True
    assert mod.LOCAL_STATIC_HTML_ONLY is True
    assert mod.BROKER_EXECUTION_ALLOWED is False
    assert mod.REAL_ORDERS_ALLOWED is False
    assert mod.REAL_MONEY_ALLOWED is False
    assert mod.AUTO_TRADING_ALLOWED is False
    assert mod.OPTION_SELLING_ALLOWED is False
    assert mod.EXTERNAL_API_ALLOWED is False
    assert mod.PROFITABILITY_CLAIM is False
    mod.assert_safety_contract()


def test_build_model_ready(tmp_path):
    create_artifacts(tmp_path)
    model = mod.build_final_launch_model(mod.FinalLaunchInputs(runs_root=tmp_path, out_dir=tmp_path / "out"))
    assert model["module"] == 138
    assert model["launch_status"] == "READY_TO_OPEN_DASHBOARD_SUITE"
    assert model["operator_status"] == "OPEN_PAPER_POSITION_MONITOR"
    assert model["latest_day_label"] == "DRY_RUN_001"
    assert model["history_status"] == "HISTORY_READY"
    assert model["total_history_records"] == 2


def test_no_artifacts(tmp_path):
    model = mod.build_final_launch_model(mod.FinalLaunchInputs(runs_root=tmp_path / "empty", out_dir=tmp_path / "out"))
    assert model["launch_status"] == "NO_DASHBOARD_ARTIFACTS_FOUND"
    assert model["present_artifacts"] == 0
    assert len(model["missing_artifacts"]) > 0


def test_write_files(tmp_path):
    create_artifacts(tmp_path)
    model = mod.build_final_launch_model(mod.FinalLaunchInputs(runs_root=tmp_path, out_dir=tmp_path / "out"))
    files = mod.write_final_launch_files(tmp_path / "out", model)
    assert Path(files["final_launch_model_json"]).exists()
    assert Path(files["final_launch_html"]).exists()
    assert Path(files["open_dashboard_suite_bat"]).exists()
    html = Path(files["final_launch_html"]).read_text(encoding="utf-8")
    assert "HQE Dashboard Final Launch Pack" in html
    assert "Safety Lock" in html
    assert "not a profitability claim" in html.lower()


def test_html_escaping(tmp_path):
    create_artifacts(tmp_path)
    model = mod.build_final_launch_model(mod.FinalLaunchInputs(runs_root=tmp_path, out_dir=tmp_path / "out"))
    model["operator_message"] = "<script>alert(1)</script>"
    html = mod.render_final_launch_html(model)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
