import json
from pathlib import Path

from src.paper_trading.improved_recorded_data_paper_rerun_planning_pack import (
    build_and_write_rerun_planning_pack,
    build_rerun_planning_report,
)


def _write_close_input(path: Path, *, phase_complete: bool = True, accepted: bool = True) -> None:
    payload = {
        "status": "pass",
        "phase_6_complete": phase_complete,
        "accepted_for_improved_paper_rerun_planning": accepted,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_accepts_safe_phase_6_close(tmp_path: Path) -> None:
    close_input = tmp_path / "close.json"
    _write_close_input(close_input)

    report = build_rerun_planning_report(
        close_input_path=close_input,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.close_report_found is True
    assert report.phase_6_complete is True
    assert report.accepted_for_improved_paper_rerun_planning is True
    assert report.accepted_for_future_improved_rerun_execution is True
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert report.plan_step_count == 5


def test_write_pack_outputs_manifest_and_steps(tmp_path: Path) -> None:
    close_input = tmp_path / "close.json"
    output_dir = tmp_path / "pack"
    _write_close_input(close_input)

    report, outputs = build_and_write_rerun_planning_pack(
        close_input_path=close_input,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "steps_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "improved_recorded_data_paper_rerun_planning_pack"
    assert manifest["accepted_for_future_improved_rerun_execution"] is True
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_close_input_stays_safe_and_does_not_accept_execution(tmp_path: Path) -> None:
    report = build_rerun_planning_report(
        close_input_path=tmp_path / "missing_close.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.close_report_found is False
    assert report.phase_6_complete is False
    assert report.accepted_for_improved_paper_rerun_planning is False
    assert report.accepted_for_future_improved_rerun_execution is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "close_input_missing" for issue in report.issues)
