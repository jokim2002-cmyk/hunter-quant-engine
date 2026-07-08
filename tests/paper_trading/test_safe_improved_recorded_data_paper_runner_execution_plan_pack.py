import json
from pathlib import Path

from src.paper_trading.safe_improved_recorded_data_paper_runner_execution_plan_pack import (
    build_and_write_execution_plan_pack,
    build_execution_plan_report,
)


def _write_phase8_report(path: Path, *, safe: bool = True) -> None:
    payload = {
        "status": "pass",
        "phase_8_complete": True,
        "accepted_for_future_improved_paper_runner_execution_phase": True,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "optimization_executed": False,
        "strategy_logic_changed": False,
    }
    if not safe:
        payload["ready_for_live_or_real_money"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_organization_report(path: Path, *, safe: bool = True) -> None:
    payload = {
        "status": "pass",
        "accepted_for_phase9_continuation": True,
        "root_runner_clutter_cleared": True,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "optimization_executed": False,
        "strategy_logic_changed": False,
    }
    if not safe:
        payload["profitability_claim_allowed"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_execution_plan_accepts_safe_prior_evidence_and_locks_all_items(tmp_path: Path) -> None:
    phase8 = tmp_path / "phase8.json"
    organization = tmp_path / "organization.json"
    _write_phase8_report(phase8)
    _write_organization_report(organization)

    report = build_execution_plan_report(
        phase8_input_path=phase8,
        organization_input_path=organization,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.phase8_report_found is True
    assert report.phase8_complete is True
    assert report.phase8_accepts_execution_phase is True
    assert report.organization_report_found is True
    assert report.organization_accepts_phase9 is True
    assert report.accepted_for_future_guarded_runner_module is True
    assert report.plan_item_count == 6
    assert report.locked_plan_item_count == 6
    assert report.runner_execution_enabled is False
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert "not a profitability claim" in report.no_profitability_claim_notice.lower()


def test_execution_plan_writes_json_text_csv_and_manifest_outputs(tmp_path: Path) -> None:
    phase8 = tmp_path / "phase8.json"
    organization = tmp_path / "organization.json"
    output_dir = tmp_path / "pack"
    _write_phase8_report(phase8)
    _write_organization_report(organization)

    report, outputs = build_and_write_execution_plan_pack(
        phase8_input_path=phase8,
        organization_input_path=organization,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ("report_json", "report_txt", "plan_csv", "manifest_json"):
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "safe_improved_recorded_data_paper_runner_execution_plan_pack"
    assert manifest["accepted_for_future_guarded_runner_module"] is True
    assert manifest["runner_execution_enabled"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["optimization_executed"] is False
    assert manifest["strategy_logic_changed"] is False
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False


def test_execution_plan_rejects_unsafe_prior_evidence_without_enabling_runner(tmp_path: Path) -> None:
    phase8 = tmp_path / "phase8.json"
    organization = tmp_path / "organization.json"
    _write_phase8_report(phase8, safe=False)
    _write_organization_report(organization)

    report = build_execution_plan_report(
        phase8_input_path=phase8,
        organization_input_path=organization,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted_for_future_guarded_runner_module is False
    assert report.runner_execution_enabled is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "unsafe_phase8_input_boundary" for issue in report.issues)
