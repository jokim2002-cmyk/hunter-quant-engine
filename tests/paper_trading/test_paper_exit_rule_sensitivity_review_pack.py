import json
from pathlib import Path

from src.paper_trading.paper_exit_rule_sensitivity_review_pack import (
    CANDIDATE_ID,
    build_and_write_exit_rule_sensitivity_pack,
    build_exit_rule_sensitivity_report,
)


def _write_tuning_input(path: Path) -> None:
    payload = {
        "candidates": [
            {
                "candidate_id": CANDIDATE_ID,
                "priority": "high",
                "status": "paper_candidate_ready",
                "title": "Exit rule sensitivity",
            }
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_slippage_input(path: Path) -> None:
    payload = {
        "report_type": "paper_slippage_and_cost_sensitivity_pack",
        "status": "pass",
        "accepted_for_future_sensitivity_review": True,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_requires_safety_boundaries(tmp_path: Path) -> None:
    tuning_input = tmp_path / "tuning.json"
    slippage_input = tmp_path / "slippage.json"
    _write_tuning_input(tuning_input)
    _write_slippage_input(slippage_input)

    report = build_exit_rule_sensitivity_report(
        tuning_input_path=tuning_input,
        slippage_input_path=slippage_input,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.candidate_found is True
    assert report.accepted_for_future_exit_rule_review is True
    assert report.slippage_cost_report_found is True
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert report.high_impact_item_count >= 3


def test_write_pack_outputs_manifest_and_reports(tmp_path: Path) -> None:
    tuning_input = tmp_path / "tuning.json"
    slippage_input = tmp_path / "slippage.json"
    output_dir = tmp_path / "pack"
    _write_tuning_input(tuning_input)
    _write_slippage_input(slippage_input)

    report, outputs = build_and_write_exit_rule_sensitivity_pack(
        tuning_input_path=tuning_input,
        slippage_input_path=slippage_input,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "items_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "paper_exit_rule_sensitivity_review_pack"
    assert manifest["slippage_cost_report_found"] is True
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_inputs_stay_safe(tmp_path: Path) -> None:
    report = build_exit_rule_sensitivity_report(
        tuning_input_path=tmp_path / "missing_tuning.json",
        slippage_input_path=tmp_path / "missing_slippage.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.candidate_found is False
    assert report.accepted_for_future_exit_rule_review is False
    assert report.slippage_cost_report_found is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "input_missing" for issue in report.issues)
