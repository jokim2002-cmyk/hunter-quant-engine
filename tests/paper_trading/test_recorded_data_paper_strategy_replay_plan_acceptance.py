import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_replay_plan_acceptance import (
    build_and_write_replay_plan_acceptance_report,
    build_replay_plan_acceptance_report,
    safety_notice,
)


def _scenario_plan(
    scenario_id="recorded_strategy_replay_scenario_001",
    planned_bar_count=2,
):
    return {
        "scenario_id": scenario_id,
        "source_path": "sample.csv",
        "source_type": "csv",
        "planned_bar_count": planned_bar_count,
        "first_timestamp": "2026-01-01T09:15:00+05:30",
        "last_timestamp": "2026-01-01T09:16:00+05:30",
        "strategy_execution_mode": "not_executed_planning_only",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "plan_manifest_only",
    }


def _plan(status="pass", ready=True, scenario_plans=None):
    plans = scenario_plans if scenario_plans is not None else [_scenario_plan()]
    return {
        "status": status,
        "ready_to_plan": ready,
        "scenario_count": len(plans),
        "total_planned_bars": sum(plan.get("planned_bar_count", 0) for plan in plans),
        "scenario_plans": plans,
    }


def _write_plan(tmp_path, payload):
    path = tmp_path / "paper_strategy_replay_plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_plan_acceptance_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_replay_plan_fails(tmp_path):
    report = build_replay_plan_acceptance_report(
        replay_plan_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "replay_plan_missing" for issue in report.issues)


def test_invalid_json_fails(tmp_path):
    path = tmp_path / "paper_strategy_replay_plan.json"
    path.write_text("{bad-json", encoding="utf-8")

    report = build_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "replay_plan_invalid_json" for issue in report.issues)


def test_invalid_shape_fails(tmp_path):
    path = _write_plan(tmp_path, ["not", "object"])

    report = build_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "replay_plan_invalid_shape" for issue in report.issues)


def test_valid_plan_is_accepted(tmp_path):
    path = _write_plan(tmp_path, _plan())

    report = build_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
        min_scenario_plans=1,
        min_total_planned_bars=1,
    )

    assert report.status == "pass"
    assert report.accepted is True
    assert report.scenario_count == 1
    assert report.total_planned_bars == 2


def test_not_ready_plan_fails(tmp_path):
    path = _write_plan(tmp_path, _plan(status="pass", ready=False))

    report = build_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "replay_plan_not_ready" for issue in report.issues)


def test_warn_plan_fails_by_default(tmp_path):
    path = _write_plan(tmp_path, _plan(status="warn", ready=True))

    report = build_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "replay_plan_warn" for issue in report.issues)


def test_warn_plan_can_be_accepted_when_allowed(tmp_path):
    path = _write_plan(tmp_path, _plan(status="warn", ready=True))

    report = build_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted is True


def test_min_scenario_plans_rule_can_fail(tmp_path):
    path = _write_plan(tmp_path, _plan(scenario_plans=[_scenario_plan()]))

    report = build_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
        min_scenario_plans=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_scenario_plans" for issue in report.issues)


def test_min_total_planned_bars_rule_can_fail(tmp_path):
    path = _write_plan(
        tmp_path,
        _plan(scenario_plans=[_scenario_plan(planned_bar_count=1)]),
    )

    report = build_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
        min_total_planned_bars=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_total_planned_bars" for issue in report.issues)


def test_wrong_modes_and_forbidden_fields_fail(tmp_path):
    plan = _scenario_plan()
    plan["strategy_execution_mode"] = "executed"
    plan["order_id"] = "not-allowed"
    path = _write_plan(tmp_path, _plan(scenario_plans=[plan]))

    report = build_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_plan_wrong_modes" for issue in report.issues)
    assert any(issue.code == "scenario_plan_forbidden_fields" for issue in report.issues)


def test_build_and_write_acceptance_contains_outputs_safety_and_no_profit_claim(tmp_path):
    path = _write_plan(tmp_path, _plan())

    report, outputs = build_and_write_replay_plan_acceptance_report(
        replay_plan_path=path,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["paper_strategy_replay_plan_acceptance_txt"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert outputs["paper_strategy_replay_plan_acceptance_json"].exists()
    assert outputs["paper_strategy_replay_plan_acceptance_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert report.accepted is True
    assert "not a profitability claim" in text_report
    assert manifest["accepted"] is True


def test_documentation_mentions_paper_strategy_replay_plan_acceptance_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_REPLAY_PLAN_ACCEPTANCE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_replay_plan_acceptance.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
