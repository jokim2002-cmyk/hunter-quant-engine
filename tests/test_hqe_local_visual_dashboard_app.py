import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hqe_local_visual_dashboard_app.py"
spec = importlib.util.spec_from_file_location("hqe_local_visual_dashboard_app", MODULE_PATH)
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)


def test_guard_check_blocks_orders_and_real_money():
    payload = app.guard_check()
    assert payload["guard_check_status"] == "PASS"
    assert payload["order_api_invoked_by_visual_dashboard"] is False
    assert payload["broker_execution_invoked_by_visual_dashboard"] is False
    assert payload["auto_trading_started_by_visual_dashboard"] is False
    assert payload["real_money_automatic"] is False
    assert payload["blocked_actions"]["place_order"] == "HARD_BLOCKED"
    assert payload["safety_lock"]["paper_only"] is True


def test_build_status_has_visual_dashboard_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "repo_root", lambda: tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for key, candidates in app.REQUIRED_SCRIPTS.items():
        p = tmp_path / candidates[0]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# safe placeholder\n", encoding="utf-8")
    payload = app.build_status(tmp_path, user_id="test-user")
    assert payload["dashboard_type"] == "LOCAL_TKINTER_GUI_WITH_SAFE_BUTTONS"
    assert payload["script_readiness"]["status"] == "PASS"
    assert payload["runtime_guards"]["order_api_invoked_by_visual_dashboard"] is False


def test_write_outputs_creates_launcher_html_json_and_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "repo_root", lambda: tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for candidates in app.REQUIRED_SCRIPTS.values():
        p = tmp_path / candidates[0]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# safe placeholder\n", encoding="utf-8")
    payload = app.write_outputs(tmp_path, user_id="test-user")
    assert Path(payload["evidence_files"]["json"]).exists()
    assert Path(payload["evidence_files"]["markdown"]).exists()
    assert Path(payload["evidence_files"]["html"]).exists()
    launcher = Path(payload["evidence_files"]["launcher_cmd"])
    assert launcher.exists()
    assert "--launch-gui" in launcher.read_text(encoding="utf-8")


def test_status_json_contains_no_secret_values(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "repo_root", lambda: tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for candidates in app.REQUIRED_SCRIPTS.values():
        p = tmp_path / candidates[0]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# safe placeholder\n", encoding="utf-8")
    payload = app.write_outputs(tmp_path, user_id="test-user")
    text = Path(payload["evidence_files"]["json"]).read_text(encoding="utf-8")
    assert "FYERS_ACCESS_TOKEN" not in text
    assert "HQE_LOCAL_PASSWORD" not in text
    assert "no_real_money" in text


def test_main_guard_check_prints_json(capsys):
    code = app.main(["--guard-check"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["guard_check_status"] == "PASS"
