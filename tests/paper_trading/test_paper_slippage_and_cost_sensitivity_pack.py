import json
from pathlib import Path

from src.paper_trading.paper_slippage_and_cost_sensitivity_pack import (
    CANDIDATE_ID,
    build_and_write_slippage_cost_pack,
    build_slippage_cost_report,
)


def _write_tuning_input(path: Path) -> None:
    payload = {
        "candidates": [
            {
                "candidate_id": CANDIDATE_ID,
                "priority": "high",
                "status": "paper_candidate_ready",
                "title": "Slippage and cost sensitivity",
            }
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_pricing_input(path: Path) -> None:
    payload = {
        "report_type": "paper_option_reference_pricing_reality_check_pack",
        "status": "pass",
        "profitability_claim_allowed": False,
        "ready_for_live_or_real_money": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_locks_safety_boundaries(tmp_path: Path) -> None:
    tuning = tmp_path / "tuning.json"
    pricing = tmp_path / "pricing.json"
    _write_tuning_input(tuning)
    _write_pricing_input(pricing)

    report = build_slippage_cost_report(
        input_path=tuning,
        pricing_reality_input_path=pricing,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.candidate_found is True
    assert report.accepted_for_future_sensitivity_review is True
    assert report.pricing_reality_report_found is True
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert report.high_impact_item_count >= 3


def test_write_pack_outputs(tmp_path: Path) -> None:
    tuning = tmp_path / "tuning.json"
    pricing = tmp_path / "pricing.json"
    output_dir = tmp_path / "pack"
    _write_tuning_input(tuning)
    _write_pricing_input(pricing)

    report, outputs = build_and_write_slippage_cost_pack(
        input_path=tuning,
        pricing_reality_input_path=pricing,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "items_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "paper_slippage_and_cost_sensitivity_pack"
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_inputs_stay_safe(tmp_path: Path) -> None:
    report = build_slippage_cost_report(
        input_path=tmp_path / "missing_tuning.json",
        pricing_reality_input_path=tmp_path / "missing_pricing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.candidate_found is False
    assert report.accepted_for_future_sensitivity_review is False
    assert report.pricing_reality_report_found is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "input_missing" for issue in report.issues)
