import json
from pathlib import Path

from src.paper_trading.paper_improvement_execution_sprint_close_pack import (
    DEFAULT_INPUTS,
    build_and_write_improvement_execution_close_pack,
    build_improvement_execution_close_report,
)


def _write_input(path: Path, *, status: str = "pass") -> None:
    payload = {
        "status": status,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _tmp_inputs(tmp_path: Path) -> dict[str, Path]:
    return {key: tmp_path / f"{key}.json" for key in DEFAULT_INPUTS}


def test_build_report_closes_phase_when_all_inputs_are_safe(tmp_path: Path) -> None:
    inputs = _tmp_inputs(tmp_path)
    for path in inputs.values():
        _write_input(path)

    report = build_improvement_execution_close_report(
        input_paths=inputs,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.found_input_count == 5
    assert report.pass_input_count == 5
    assert report.missing_input_count == 0
    assert report.accepted_for_improved_paper_rerun_planning is True
    assert report.phase_6_complete is True
    assert report.completed_total_after_module == 105
    assert report.phase_6_pending_after_module == 0
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_write_pack_outputs_manifest_and_inputs_csv(tmp_path: Path) -> None:
    inputs = _tmp_inputs(tmp_path)
    for path in inputs.values():
        _write_input(path)
    output_dir = tmp_path / "pack"

    report, outputs = build_and_write_improvement_execution_close_pack(
        input_paths=inputs,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "inputs_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "paper_improvement_execution_sprint_close_pack"
    assert manifest["phase_6_complete"] is True
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_inputs_do_not_close_phase_or_allow_profit_claim(tmp_path: Path) -> None:
    inputs = _tmp_inputs(tmp_path)

    report = build_improvement_execution_close_report(
        input_paths=inputs,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.found_input_count == 0
    assert report.missing_input_count == 5
    assert report.accepted_for_improved_paper_rerun_planning is False
    assert report.phase_6_complete is False
    assert report.phase_6_pending_after_module == 1
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
