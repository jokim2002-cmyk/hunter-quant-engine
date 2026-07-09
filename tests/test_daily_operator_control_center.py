from __future__ import annotations

from pathlib import Path

from scripts.run_daily_operator_control_center import (
    SAFETY_LOCK,
    build_control_center,
    command_is_safe,
    summarize_status,
    StepResult,
)


def _write_stub_script(path: Path, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "import argparse\n"
            "parser = argparse.ArgumentParser()\n"
            "parser.add_argument('--runs-root')\n"
            "parser.add_argument('--print-summary', action='store_true')\n"
            "args = parser.parse_args()\n"
            f"print('{label}_CREATED')\n"
            "print('safety=paper_only_no_broker_no_real_orders_no_auto_trading_no_option_selling_no_profitability_claim')\n"
        ),
        encoding="utf-8",
    )


def test_module144_plan_only_creates_control_center_outputs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    tests_dir = repo_root / "tests"
    scripts_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    _write_stub_script(scripts_dir / "build_daily_workflow_operator_checklist.py", "MODULE_141")
    _write_stub_script(scripts_dir / "validate_daily_workflow_evidence_handoff.py", "MODULE_142")
    _write_stub_script(scripts_dir / "build_daily_workflow_evidence_browser.py", "MODULE_143")

    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    report = build_control_center(
        repo_root=repo_root,
        runs_root=runs_root,
        output_dir=tmp_path / "control",
        execute_approved_steps=False,
    )

    assert report["control_center_status"] == "READY_PLAN_ONLY"
    assert all(step["status"] == "PLANNED_NOT_EXECUTED" for step in report["steps"])
    assert report["safety_lock"] == SAFETY_LOCK
    assert report["safety_lock"]["real_money"] is False
    assert report["safety_lock"]["broker_execution"] is False
    assert report["safety_lock"]["real_orders"] is False
    assert report["safety_lock"]["auto_trading"] is False
    assert report["safety_lock"]["option_selling"] is False
    assert report["safety_lock"]["external_api"] is False
    assert report["safety_lock"]["profitability_claim"] is False

    assert Path(report["outputs"]["html"]).exists()
    assert Path(report["outputs"]["json"]).exists()
    assert Path(report["outputs"]["markdown"]).exists()
    assert Path(report["outputs"]["steps_csv"]).exists()

    markdown = Path(report["outputs"]["markdown"]).read_text(encoding="utf-8")
    html = Path(report["outputs"]["html"]).read_text(encoding="utf-8")
    assert "This is not a profitability claim" in markdown
    assert "Control-center status: `READY_PLAN_ONLY`" in markdown
    assert "paper/simulation only" in html.lower()


def test_module144_holds_when_required_script_missing_in_plan_mode(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    tests_dir = repo_root / "tests"
    scripts_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    _write_stub_script(scripts_dir / "build_daily_workflow_operator_checklist.py", "MODULE_141")
    # Module 142 intentionally missing.
    _write_stub_script(scripts_dir / "build_daily_workflow_evidence_browser.py", "MODULE_143")

    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    report = build_control_center(
        repo_root=repo_root,
        runs_root=runs_root,
        output_dir=tmp_path / "control",
        execute_approved_steps=False,
    )

    assert report["control_center_status"] == "HOLD_REQUIRED_SCRIPT_MISSING"
    assert any(step["status"] == "MISSING_REQUIRED_SCRIPT" for step in report["steps"])


def test_module144_command_safety_allow_list_blocks_external_or_non_repo_script(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    safe_script = scripts_dir / "safe.py"
    safe_script.write_text("print('safe')", encoding="utf-8")

    assert command_is_safe(["python.exe", str(safe_script), "--runs-root", str(tmp_path)], repo_root)

    outside_script = tmp_path / "outside.py"
    outside_script.write_text("print('outside')", encoding="utf-8")
    assert not command_is_safe(["python.exe", str(outside_script)], repo_root)

    assert not command_is_safe(["python.exe", str(safe_script), "https://example.com"], repo_root)
    assert not command_is_safe(["python.exe", str(safe_script), "place_order"], repo_root)
    assert not command_is_safe(["python.exe", str(safe_script), "api_key"], repo_root)


def test_module144_status_summary_blocks_and_holds() -> None:
    def step(status: str) -> StepResult:
        return StepResult(
            step_id=status,
            title=status,
            script_path=None,
            status=status,
            return_code=None,
            stdout_tail="",
            command=[],
            started_at="2026-07-09T09:15:00",
            finished_at="2026-07-09T09:15:01",
        )

    assert summarize_status([step("PASS"), step("PASS")]) == "PASS"
    assert summarize_status([step("PLANNED_NOT_EXECUTED"), step("PLANNED_NOT_EXECUTED")]) == "READY_PLAN_ONLY"
    assert summarize_status([step("MISSING_REQUIRED_SCRIPT")]) == "HOLD_REQUIRED_SCRIPT_MISSING"
    assert summarize_status([step("FAIL")]) == "HOLD_STEP_FAILURE"
    assert summarize_status([step("BLOCKED_UNSAFE_COMMAND")]) == "BLOCKED_SAFETY_RISK"
