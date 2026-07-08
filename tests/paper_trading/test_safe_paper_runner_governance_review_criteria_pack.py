import json
from pathlib import Path

from src.paper_trading.safe_paper_runner_governance_review_criteria_pack import (
    build_and_write_governance_criteria_pack,
    build_governance_criteria_report,
)


def _write_readiness(path: Path, *, safe: bool = True, started: bool = True) -> None:
    payload = {
        "status": "pass",
        "phase12_started": started,
        "accepted_for_future_safe_paper_runner_governance_review_criteria": True,
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


def test_governance_criteria_accepts_safe_readiness_and_locks_criteria(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.json"
    _write_readiness(readiness)

    report = build_governance_criteria_report(
        governance_readiness_input_path=readiness,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.governance_readiness_found is True
    assert report.governance_readiness_status == "pass"
    assert report.phase12_started is True
    assert report.readiness_accepts_criteria is True
    assert report.accepted_for_future_safe_paper_runner_governance_review_close is True
    assert report.criterion_count == 6
    assert report.locked_criterion_count == 6
    assert report.criteria_mode == "governance_review_criteria_only"
    assert report.runner_execution_enabled is False
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_governance_criteria_writes_json_text_csv_and_manifest(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.json"
    output_dir = tmp_path / "pack"
    _write_readiness(readiness)

    report, outputs = build_and_write_governance_criteria_pack(
        governance_readiness_input_path=readiness,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ("report_json", "report_txt", "criteria_csv", "manifest_json"):
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "safe_paper_runner_governance_review_criteria_pack"
    assert manifest["accepted_for_future_safe_paper_runner_governance_review_close"] is True
    assert manifest["criteria_mode"] == "governance_review_criteria_only"
    assert manifest["runner_execution_enabled"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["optimization_executed"] is False
    assert manifest["strategy_logic_changed"] is False
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False


def test_governance_criteria_rejects_unsafe_readiness_without_live_readiness(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.json"
    _write_readiness(readiness, safe=False)

    report = build_governance_criteria_report(
        governance_readiness_input_path=readiness,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted_for_future_safe_paper_runner_governance_review_close is False
    assert report.runner_execution_enabled is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(
        issue["code"] == "unsafe_governance_readiness_input_boundary"
        for issue in report.issues
    )
