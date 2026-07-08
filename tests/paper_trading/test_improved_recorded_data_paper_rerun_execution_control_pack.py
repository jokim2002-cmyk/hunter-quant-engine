import json
from pathlib import Path

from src.paper_trading.improved_recorded_data_paper_rerun_execution_control_pack import (
    build_and_write_execution_control_pack,
    build_execution_control_report,
)


def _write_preflight_input(path: Path, *, accepted: bool = True) -> None:
    payload = {
        "status": "pass",
        "accepted_for_future_improved_rerun_runner": accepted,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_accepts_safe_preflight_and_locks_controls(tmp_path: Path) -> None:
    preflight_input = tmp_path / "preflight.json"
    _write_preflight_input(preflight_input)

    report = build_execution_control_report(
        preflight_input_path=preflight_input,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.preflight_report_found is True
    assert report.preflight_accepts_future_runner is True
    assert report.accepted_for_future_improved_paper_rerun is True
    assert report.control_count == 6
    assert report.locked_control_count == 6
    assert report.runner_output_contract_locked is True
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_write_pack_outputs_manifest_and_controls(tmp_path: Path) -> None:
    preflight_input = tmp_path / "preflight.json"
    output_dir = tmp_path / "pack"
    _write_preflight_input(preflight_input)

    report, outputs = build_and_write_execution_control_pack(
        preflight_input_path=preflight_input,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "controls_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "improved_recorded_data_paper_rerun_execution_control_pack"
    assert manifest["accepted_for_future_improved_paper_rerun"] is True
    assert manifest["runner_output_contract_locked"] is True
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_preflight_stays_safe_and_does_not_accept_rerun(tmp_path: Path) -> None:
    report = build_execution_control_report(
        preflight_input_path=tmp_path / "missing_preflight.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.preflight_report_found is False
    assert report.accepted_for_future_improved_paper_rerun is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "preflight_input_missing" for issue in report.issues)
