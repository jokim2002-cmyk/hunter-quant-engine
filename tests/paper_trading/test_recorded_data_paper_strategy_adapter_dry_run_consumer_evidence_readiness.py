import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness import (
    build_adapter_dry_run_consumer_evidence_readiness_report,
    build_and_write_adapter_dry_run_consumer_evidence_readiness_report,
    safety_notice,
)


def _plan_readiness(status="pass", ready=True):
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


def _replay_plan(status="pass", ready=True, plans=None):
    scenario_plans = plans if plans is not None else [_scenario_plan()]
    return {
        "status": status,
        "ready_to_plan": ready,
        "scenario_count": len(scenario_plans),
        "total_planned_bars": sum(
            plan.get("planned_bar_count", 0) for plan in scenario_plans
        ),
        "scenario_plans": scenario_plans,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _inputs(tmp_path, readiness=None, plan=None):
    readiness_path = _write_json(
        tmp_path / "paper_strategy_replay_plan_readiness.json",
        readiness or _plan_readiness(),
    )
    plan_path = _write_json(
        tmp_path / "paper_strategy_replay_plan.json",
        plan or _replay_plan(),
    )
    return readiness_path, plan_path


def _build(tmp_path, **kwargs):
    readiness, plan = _inputs(
        tmp_path,
        readiness=kwargs.pop("readiness", None),
        plan=kwargs.pop("plan", None),
    )
    return build_adapter_dry_run_consumer_evidence_readiness_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        adapter_contract_output_dir=tmp_path / "adapter_contract",
        adapter_contract_acceptance_output_dir=tmp_path / "adapter_contract_acceptance",
        adapter_readiness_output_dir=tmp_path / "adapter_readiness",
        adapter_dry_run_output_dir=tmp_path / "adapter_dry_run",
        adapter_dry_run_acceptance_output_dir=tmp_path / "adapter_dry_run_acceptance",
        adapter_dry_run_readiness_output_dir=tmp_path / "adapter_dry_run_readiness",
        adapter_evidence_bundle_output_dir=tmp_path / "adapter_evidence_bundle",
        adapter_evidence_bundle_acceptance_output_dir=(
            tmp_path / "adapter_evidence_bundle_acceptance"
        ),
        adapter_evidence_readiness_output_dir=tmp_path / "adapter_evidence_readiness",
        consumer_output_dir=tmp_path / "consumer",
        consumer_acceptance_output_dir=tmp_path / "consumer_acceptance",
        consumer_readiness_output_dir=tmp_path / "consumer_readiness",
        consumer_evidence_bundle_output_dir=tmp_path / "consumer_evidence_bundle",
        consumer_evidence_bundle_acceptance_output_dir=(
            tmp_path / "consumer_evidence_bundle_acceptance"
        ),
        readiness_output_dir=tmp_path / "consumer_evidence_readiness",
        **kwargs,
    )


def test_safety_notice_preserves_consumer_evidence_readiness_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not execute strategy logic" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_consumer_evidence_readiness_passes_valid_inputs(tmp_path):
    report = _build(tmp_path)

    assert report.status == "pass"
    assert report.ready_for_future_consumer_evidence_release is True
    assert [stage.stage for stage in report.stage_results] == [
        "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle",
        "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance",
    ]


def test_consumer_evidence_readiness_fails_when_min_requests_not_met(tmp_path):
    report = _build(tmp_path, min_requests=2)

    assert report.status == "fail"
    assert report.ready_for_future_consumer_evidence_release is False
    assert report.stage_results[0].accepted is False


def test_consumer_evidence_readiness_fails_when_min_total_bars_not_met(tmp_path):
    report = _build(tmp_path, min_total_planned_bars=3)

    assert report.status == "fail"
    assert report.stage_results[1].accepted is False


def test_consumer_evidence_readiness_blocks_warning_by_default(tmp_path):
    report = _build(
        tmp_path,
        readiness=_plan_readiness(status="warn", ready=True),
    )

    assert report.status == "fail"
    assert report.ready_for_future_consumer_evidence_release is False


def test_consumer_evidence_readiness_allows_warning_when_requested(tmp_path):
    report = _build(
        tmp_path,
        readiness=_plan_readiness(status="warn", ready=True),
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_consumer_evidence_release is True
    assert report.stage_results[1].accepted is True


def test_consumer_evidence_readiness_fails_invalid_plan_readiness(tmp_path):
    report = _build(
        tmp_path,
        readiness=_plan_readiness(status="fail", ready=False),
    )

    assert report.status == "fail"
    assert report.stage_results[0].status == "fail"


def test_consumer_evidence_readiness_fails_wrong_replay_plan_modes(tmp_path):
    scenario = _scenario_plan()
    scenario["strategy_execution_mode"] = "executed"

    report = _build(tmp_path, plan=_replay_plan(plans=[scenario]))

    assert report.status == "fail"
    assert report.stage_results[0].accepted is False


def test_consumer_evidence_readiness_fails_forbidden_replay_plan_fields(tmp_path):
    plan = _replay_plan()
    plan["pnl"] = 99

    report = _build(tmp_path, plan=plan)

    assert report.status == "fail"
    assert report.stage_results[0].accepted is False


def test_build_and_write_consumer_evidence_readiness_outputs_safety_and_no_profit_claim(
    tmp_path,
):
    readiness, plan = _inputs(tmp_path)

    report, outputs = build_and_write_adapter_dry_run_consumer_evidence_readiness_report(
        plan_readiness_path=readiness,
        replay_plan_path=plan,
        adapter_contract_output_dir=tmp_path / "adapter_contract",
        adapter_contract_acceptance_output_dir=tmp_path / "adapter_contract_acceptance",
        adapter_readiness_output_dir=tmp_path / "adapter_readiness",
        adapter_dry_run_output_dir=tmp_path / "adapter_dry_run",
        adapter_dry_run_acceptance_output_dir=tmp_path / "adapter_dry_run_acceptance",
        adapter_dry_run_readiness_output_dir=tmp_path / "adapter_dry_run_readiness",
        adapter_evidence_bundle_output_dir=tmp_path / "adapter_evidence_bundle",
        adapter_evidence_bundle_acceptance_output_dir=(
            tmp_path / "adapter_evidence_bundle_acceptance"
        ),
        adapter_evidence_readiness_output_dir=tmp_path / "adapter_evidence_readiness",
        consumer_output_dir=tmp_path / "consumer",
        consumer_acceptance_output_dir=tmp_path / "consumer_acceptance",
        consumer_readiness_output_dir=tmp_path / "consumer_readiness",
        consumer_evidence_bundle_output_dir=tmp_path / "consumer_evidence_bundle",
        consumer_evidence_bundle_acceptance_output_dir=(
            tmp_path / "consumer_evidence_bundle_acceptance"
        ),
        readiness_output_dir=tmp_path / "consumer_evidence_readiness",
    )

    text_report = outputs[
        "paper_strategy_adapter_dry_run_consumer_evidence_readiness_txt"
    ].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["paper_strategy_adapter_dry_run_consumer_evidence_readiness_json"].exists()
    assert outputs["paper_strategy_adapter_dry_run_consumer_evidence_readiness_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_consumer_evidence_release"] is True


def test_documentation_mentions_consumer_evidence_readiness_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_ADAPTER_DRY_RUN_CONSUMER_EVIDENCE_READINESS.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
