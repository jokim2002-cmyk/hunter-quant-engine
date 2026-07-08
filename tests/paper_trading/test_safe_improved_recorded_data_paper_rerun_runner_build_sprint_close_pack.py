import json
from pathlib import Path

from src.paper_trading.safe_improved_recorded_data_paper_rerun_runner_build_sprint_close_pack import (
    DEFAULT_INPUTS,
    build_and_write_phase8_close_pack,
    build_phase8_close_report,
)


def _write_input(path: Path, accepted_flag: str) -> None:
    payload = {
        "status": "pass",
        accepted_flag: True,
        "runner_execution_enabled": False,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _tmp_inputs(tmp_path: Path) -> dict[str, Path]:
    return {key: tmp_path / f"{key}.json" for key in DEFAULT_INPUTS}


def test_build_report_closes_phase8_when_inputs_are_safe_and_accepted(tmp_path: Path) -> None:
    inputs = _tmp_inputs(tmp_path)
    _write_input(inputs["scaffold"], "accepted_for_future_runner_dry_run_pack")
    _write_input(inputs["dry_run_validation"], "accepted_for_future_runner_close_pack")

    report = build_phase8_close_report(
        input_paths=inputs,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.found_input_count == 2
    assert report.pass_input_count == 2
    assert report.accepted_input_count == 2
    assert report.missing_input_count == 0
    assert report.runner_execution_enabled_input_count == 0
    assert report.phase_8_complete is True
    assert report.accepted_for_future_improved_paper_runner_execution_phase is True
    assert report.completed_total_after_module == 112
    assert report.phase_8_pending_after_module == 0
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_write_pack_outputs_manifest_and_inputs_csv(tmp_path: Path) -> None:
    inputs = _tmp_inputs(tmp_path)
    _write_input(inputs["scaffold"], "accepted_for_future_runner_dry_run_pack")
    _write_input(inputs["dry_run_validation"], "accepted_for_future_runner_close_pack")
    output_dir = tmp_path / "pack"

    report, outputs = build_and_write_phase8_close_pack(
        input_paths=inputs,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "inputs_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "safe_improved_recorded_data_paper_rerun_runner_build_sprint_close_pack"
    assert manifest["phase_8_complete"] is True
    assert manifest["accepted_for_future_improved_paper_runner_execution_phase"] is True
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_inputs_do_not_close_phase_or_allow_profit_claim(tmp_path: Path) -> None:
    inputs = _tmp_inputs(tmp_path)

    report = build_phase8_close_report(
        input_paths=inputs,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.found_input_count == 0
    assert report.missing_input_count == 2
    assert report.phase_8_complete is False
    assert report.accepted_for_future_improved_paper_runner_execution_phase is False
    assert report.phase_8_pending_after_module == 1
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
