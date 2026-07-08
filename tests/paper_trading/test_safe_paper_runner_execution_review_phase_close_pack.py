import json
from pathlib import Path

from src.paper_trading.safe_paper_runner_execution_review_phase_close_pack import (
    build_and_write_phase11_close_pack,
    build_phase11_close_report,
)


def _write_criteria(path: Path, *, safe: bool = True, accepted: bool = True) -> None:
    payload = {
        "status": "pass",
        "accepted_for_future_safe_paper_runner_execution_review_close": accepted,
        "runner_execution_enabled": False,
        "backtest_executed": False,
        "optimization_executed": False,
        "strategy_logic_changed": False,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
    }
    if not safe:
        payload["ready_for_live_or_real_money"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_phase11_close_accepts_safe_criteria_and_closes_phase11(tmp_path: Path) -> None:
    criteria = tmp_path / "criteria.json"
    _write_criteria(criteria)

    report = build_phase11_close_report(
        execution_review_criteria_input_path=criteria,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.execution_review_criteria_found is True
    assert report.execution_review_criteria_status == "pass"
    assert report.execution_review_criteria_accepts_close is True
    assert report.phase_11_complete is True
    assert report.accepted_for_future_phase12_safe_paper_runner_governance_review is True
    assert report.close_item_count == 6
    assert report.passed_close_item_count == 6
    assert report.close_mode == "phase_close_only"
    assert report.runner_execution_enabled is False
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_phase11_close_writes_json_text_csv_and_manifest(tmp_path: Path) -> None:
    criteria = tmp_path / "criteria.json"
    output_dir = tmp_path / "pack"
    _write_criteria(criteria)

    report, outputs = build_and_write_phase11_close_pack(
        execution_review_criteria_input_path=criteria,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ("report_json", "report_txt", "close_csv", "manifest_json"):
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "safe_paper_runner_execution_review_phase_close_pack"
    assert manifest["phase_11_complete"] is True
    assert manifest["accepted_for_future_phase12_safe_paper_runner_governance_review"] is True
    assert manifest["close_mode"] == "phase_close_only"
    assert manifest["runner_execution_enabled"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["optimization_executed"] is False
    assert manifest["strategy_logic_changed"] is False
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False


def test_phase11_close_rejects_unsafe_criteria_without_live_or_profit_claim(tmp_path: Path) -> None:
    criteria = tmp_path / "criteria.json"
    _write_criteria(criteria, safe=False)

    report = build_phase11_close_report(
        execution_review_criteria_input_path=criteria,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.phase_11_complete is False
    assert report.accepted_for_future_phase12_safe_paper_runner_governance_review is False
    assert report.runner_execution_enabled is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(
        issue["code"] == "unsafe_execution_review_criteria_input_boundary"
        for issue in report.issues
    )
