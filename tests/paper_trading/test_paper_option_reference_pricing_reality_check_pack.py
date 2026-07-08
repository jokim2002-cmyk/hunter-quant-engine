import json
from pathlib import Path

from src.paper_trading.paper_option_reference_pricing_reality_check_pack import (
    CANDIDATE_ID,
    build_and_write_pricing_reality_pack,
    build_pricing_reality_report,
)


def _write_input(path: Path) -> None:
    payload = {
        "candidates": [
            {
                "candidate_id": CANDIDATE_ID,
                "priority": "high",
                "status": "paper_candidate_ready",
                "title": "Option reference pricing reality check",
            }
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_locks_safety_boundaries(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    _write_input(input_path)

    report = build_pricing_reality_report(
        input_path=input_path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.candidate_found is True
    assert report.accepted_for_future_reality_check is True
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert report.high_impact_item_count >= 3


def test_write_pack_outputs(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "pack"
    _write_input(input_path)

    report, outputs = build_and_write_pricing_reality_pack(
        input_path=input_path,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "items_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "paper_option_reference_pricing_reality_check_pack"
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False


def test_missing_input_stays_safe(tmp_path: Path) -> None:
    report = build_pricing_reality_report(
        input_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.candidate_found is False
    assert report.accepted_for_future_reality_check is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "input_missing" for issue in report.issues)
