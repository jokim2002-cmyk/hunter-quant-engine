import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_forward_paper_daily_workflow.py"
SPEC = importlib.util.spec_from_file_location("run_forward_paper_daily_workflow", SCRIPT_PATH)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

def create_dummy_scripts(repo: Path) -> None:
    for step in mod.STEP_DEFINITIONS:
        path = repo / step["script"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "import argparse, json\n"
            "from pathlib import Path\n"
            "p=argparse.ArgumentParser(); p.add_argument('--runs-root'); p.add_argument('--out-dir')\n"
            "a=p.parse_args(); Path(a.out_dir).mkdir(parents=True, exist_ok=True)\n"
            "(Path(a.out_dir)/'ok.json').write_text(json.dumps({'ok': True}), encoding='utf-8')\n"
            "print(json.dumps({'ok': True, 'out_dir': a.out_dir}))\n",
            encoding="utf-8",
        )

def test_safety_contract():
    assert mod.PAPER_ONLY is True
    assert mod.READ_ONLY_WORKFLOW_WRAPPER is True
    assert mod.LOCAL_ONLY is True
    assert mod.BROKER_EXECUTION_ALLOWED is False
    assert mod.REAL_ORDERS_ALLOWED is False
    assert mod.REAL_MONEY_ALLOWED is False
    assert mod.AUTO_TRADING_ALLOWED is False
    assert mod.OPTION_SELLING_ALLOWED is False
    assert mod.EXTERNAL_API_ALLOWED is False
    assert mod.PROFITABILITY_CLAIM is False
    mod.assert_safety_contract()

def test_plan_ready(tmp_path):
    repo = tmp_path / "repo"
    create_dummy_scripts(repo)
    model = mod.build_daily_workflow_model(
        mod.WorkflowInputs(repo, tmp_path / "runs", tmp_path / "out", sys.executable, False)
    )
    assert model["module"] == 140
    assert model["workflow_status"] == "DAILY_WORKFLOW_PLAN_READY"
    assert model["workflow_decision"] == "PLAN_READY_PAPER_ONLY"
    assert model["missing_scripts"] == []
    assert model["executed_steps"] == []

def test_execute_dummy_steps(tmp_path):
    repo = tmp_path / "repo"
    create_dummy_scripts(repo)
    model = mod.build_daily_workflow_model(
        mod.WorkflowInputs(repo, tmp_path / "runs", tmp_path / "out", sys.executable, True)
    )
    assert model["workflow_status"] == "DAILY_WORKFLOW_EXECUTION_PASS"
    assert model["workflow_decision"] == "DAILY_WORKFLOW_READY_PAPER_ONLY"
    assert len(model["executed_steps"]) == len(mod.STEP_DEFINITIONS)
    assert all(step["passed"] for step in model["executed_steps"])

def test_missing_scripts_review(tmp_path):
    model = mod.build_daily_workflow_model(
        mod.WorkflowInputs(tmp_path / "repo", tmp_path / "runs", tmp_path / "out", sys.executable, False)
    )
    assert model["workflow_status"] == "DAILY_WORKFLOW_PLAN_REVIEW_REQUIRED"
    assert model["workflow_decision"] == "REVIEW_REQUIRED_PAPER_ONLY"
    assert len(model["missing_scripts"]) == len(mod.STEP_DEFINITIONS)

def test_write_files_and_escape(tmp_path):
    repo = tmp_path / "repo"
    create_dummy_scripts(repo)
    model = mod.build_daily_workflow_model(
        mod.WorkflowInputs(repo, tmp_path / "runs", tmp_path / "out", sys.executable, True)
    )
    files = mod.write_daily_workflow_files(tmp_path / "out", model)
    assert Path(files["daily_workflow_model_json"]).exists()
    assert Path(files["daily_workflow_report_md"]).exists()
    assert Path(files["daily_workflow_summary_csv"]).exists()
    assert Path(files["daily_workflow_html"]).exists()
    assert Path(files["run_daily_workflow_bat"]).exists()

    model["workflow_status"] = "<script>alert(1)</script>"
    html = mod.render_workflow_html(model)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "not a profitability claim" in html.lower()
