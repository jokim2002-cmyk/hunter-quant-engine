import json
from pathlib import Path

from src.paper_trading.paper_signal_cooldown_duplicate_filter_review_pack import (
    CANDIDATE_ID,
    build_and_write_cooldown_duplicate_review_pack,
    build_cooldown_duplicate_review_report,
)


def _write_tuning_input(path: Path) -> None:
    payload = {
        "candidates": [
            {
                "candidate_id": CANDIDATE_ID,
                "priority": "high",
                "status": "paper_candidate_ready",
                "title": "Signal cooldown and duplicate filter",
            }
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_json(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"status": "pass"}), encoding="utf-8")


def test_build_report_locks_safety_boundaries(tmp_path: Path) -> None:
    tuning_input = tmp_path / "tuning.json"
    exit_review_input = tmp_path / "exit.json"
    guard_input = tmp_path / "guard.json"
    _write_tuning_input(tuning_input)
    _write_json(exit_review_input)
    _write_json(guard_input)

    report = build_cooldown_duplicate_review_report(
        tuning_input_path=tuning_input,
        exit_review_input_path=exit_review_input,
        frequency_guard_input_path=guard_input,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.candidate_found is True
    assert report.accepted_for_future_cooldown_duplicate_review is True
    assert report.exit_review_report_found is True
    assert report.frequency_guard_report_found is True
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert report.high_impact_item_count >= 3


def test_write_pack_outputs_manifest_and_items(tmp_path: Path) -> None:
    tuning_input = tmp_path / "tuning.json"
    exit_review_input = tmp_path / "exit.json"
    guard_input = tmp_path / "guard.json"
    output_dir = tmp_path / "pack"
    _write_tuning_input(tuning_input)
    _write_json(exit_review_input)
    _write_json(guard_input)

    report, outputs = build_and_write_cooldown_duplicate_review_pack(
        tuning_input_path=tuning_input,
        exit_review_input_path=exit_review_input,
        frequency_guard_input_path=guard_input,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "items_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "paper_signal_cooldown_duplicate_filter_review_pack"
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_inputs_stay_safe_and_do_not_allow_profit_claim(tmp_path: Path) -> None:
    report = build_cooldown_duplicate_review_report(
        tuning_input_path=tmp_path / "missing_tuning.json",
        exit_review_input_path=tmp_path / "missing_exit.json",
        frequency_guard_input_path=tmp_path / "missing_guard.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.candidate_found is False
    assert report.accepted_for_future_cooldown_duplicate_review is False
    assert report.exit_review_report_found is False
    assert report.frequency_guard_report_found is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert {issue["code"] for issue in report.issues} >= {
        "tuning_input_missing",
        "exit_review_input_missing",
        "frequency_guard_input_missing",
        "candidate_missing",
    }
