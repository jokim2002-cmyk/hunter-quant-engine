import json
from pathlib import Path

from src.paper_trading.improved_recorded_data_paper_rerun_preflight_pack import (
    build_and_write_rerun_preflight_pack,
    build_rerun_preflight_report,
)


def _write_planning_input(path: Path, *, accepted: bool = True) -> None:
    payload = {
        "status": "pass",
        "accepted_for_future_improved_rerun_execution": accepted,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_dataset(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-06-01 09:15:00,100,101,99,100.5,1000\n",
        encoding="utf-8",
    )


def test_build_report_accepts_safe_preflight(tmp_path: Path) -> None:
    planning_input = tmp_path / "planning.json"
    dataset = tmp_path / "recorded.csv"
    _write_planning_input(planning_input)
    _write_dataset(dataset)

    report = build_rerun_preflight_report(
        planning_input_path=planning_input,
        dataset_path=dataset,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.planning_report_found is True
    assert report.planning_accepts_future_execution is True
    assert report.dataset_found is True
    assert report.dataset_record_count == 1
    assert report.failed_check_count == 0
    assert report.accepted_for_future_improved_rerun_runner is True
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_write_pack_outputs_manifest_and_checks(tmp_path: Path) -> None:
    planning_input = tmp_path / "planning.json"
    dataset = tmp_path / "recorded.csv"
    output_dir = tmp_path / "pack"
    _write_planning_input(planning_input)
    _write_dataset(dataset)

    report, outputs = build_and_write_rerun_preflight_pack(
        planning_input_path=planning_input,
        dataset_path=dataset,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "checks_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "improved_recorded_data_paper_rerun_preflight_pack"
    assert manifest["accepted_for_future_improved_rerun_runner"] is True
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_inputs_fail_preflight_but_stay_safe(tmp_path: Path) -> None:
    report = build_rerun_preflight_report(
        planning_input_path=tmp_path / "missing_planning.json",
        dataset_path=tmp_path / "missing_dataset.csv",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.planning_report_found is False
    assert report.dataset_found is False
    assert report.accepted_for_future_improved_rerun_runner is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "planning_input_missing" for issue in report.issues)
