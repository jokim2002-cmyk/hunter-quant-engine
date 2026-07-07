import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_adapter_contract import (
    build_adapter_contract_report,
    build_and_write_adapter_contract_report,
    safety_notice,
)


def _readiness(status="pass", ready=True):
    return {
        "status": status,
        "ready_for_future_paper_strategy_replay_plan": ready,
    }


def _scenario_plan(bar_count=2):
    return {
        "scenario_id": "recorded_strategy_replay_scenario_001",
        "source_path": "sample.csv",
        "source_type": "csv",
        "planned_bar_count": bar_count,
        "first_timestamp": "2026-01-01T09:15:00+05:30",
        "last_timestamp": "2026-01-01T09:16:00+05:30",
        "strategy_execution_mode": "not_executed_planning_only",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "plan_manifest_only",
    }


def _plan(status="pass", ready=True, plans=None):
    scenario_plans = plans if plans is not None else [_scenario_plan()]
    return {
        "status": status,
        "ready_to_plan": ready,
        "scenario_count": len(scenario_plans),
        "total_planned_bars": sum(item.get("planned_bar_count", 0) for item in scenario_plans),
        "scenario_plans": scenario_plans,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _inputs(tmp_path, readiness=None, plan=None):
    readiness_path = _write_json(tmp_path / "plan_readiness.json", readiness or _readiness())
    plan_path = _write_json(tmp_path / "paper_strategy_replay_plan.json", plan or _plan())
    return readiness_path, plan_path


def test_safety_notice_preserves_adapter_contract_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not execute strategy logic" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_plan_readiness_fails(tmp_path):
    _, plan = _inputs(tmp_path)

    report = build_adapter_contract_report(
        plan_readiness_path=tmp_path / "missing.json",
        replay_plan_path=plan,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "plan_readiness_missing" for issue in report.issues)


def test_missing_replay_plan_fails(tmp_path):
    readiness, _ = _inputs(tmp_path)

    report = build_adapter_contract_report(
        plan_readiness_path=readiness,
        replay_plan_path=tmp_path / "missing_plan.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "replay_plan_missing" for issue in report.issues)


def test_valid_inputs_create_adapter_request(tmp_path):
    readiness, plan = _inputs(tmp_path)

    report = build_adapter_contract_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_adapter is True
    assert report.request_count == 1
    assert report.total_planned_bars == 2
    assert report.adapter_requests[0].adapter_mode == "contract_only_no_strategy_execution"


def test_warning_readiness_fails_by_default(tmp_path):
    readiness, plan = _inputs(tmp_path, readiness=_readiness(status="warn", ready=True))

    report = build_adapter_contract_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "plan_readiness_warn" for issue in report.issues)


def test_warning_readiness_can_remain_warning_when_allowed(tmp_path):
    readiness, plan = _inputs(tmp_path, readiness=_readiness(status="warn", ready=True))

    report = build_adapter_contract_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_adapter is True


def test_min_requests_rule_can_fail(tmp_path):
    readiness, plan = _inputs(tmp_path)

    report = build_adapter_contract_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        output_dir=tmp_path / "out",
        min_requests=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_adapter_requests" for issue in report.issues)


def test_min_total_planned_bars_rule_can_fail(tmp_path):
    readiness, plan = _inputs(tmp_path, plan=_plan(plans=[_scenario_plan(bar_count=1)]))

    report = build_adapter_contract_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        output_dir=tmp_path / "out",
        min_total_planned_bars=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_total_planned_bars" for issue in report.issues)


def test_wrong_modes_fail_contract(tmp_path):
    scenario = _scenario_plan()
    scenario["strategy_execution_mode"] = "executed"
    readiness, plan = _inputs(tmp_path, plan=_plan(plans=[scenario]))

    report = build_adapter_contract_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_plan_wrong_modes" for issue in report.issues)


def test_forbidden_fields_fail_contract(tmp_path):
    scenario = _scenario_plan()
    scenario["order_id"] = "not-allowed"
    readiness, plan = _inputs(tmp_path, plan=_plan(plans=[scenario]))

    report = build_adapter_contract_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_plan_forbidden_fields" for issue in report.issues)


def test_build_and_write_contract_outputs_safety_and_no_profit_claim(tmp_path):
    readiness, plan = _inputs(tmp_path)

    report, outputs = build_and_write_adapter_contract_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["paper_strategy_adapter_contract_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["paper_strategy_adapter_contract_json"].exists()
    assert outputs["paper_strategy_adapter_requests_jsonl"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_adapter"] is True


def test_documentation_mentions_adapter_contract_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_ADAPTER_CONTRACT.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_adapter_contract.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
