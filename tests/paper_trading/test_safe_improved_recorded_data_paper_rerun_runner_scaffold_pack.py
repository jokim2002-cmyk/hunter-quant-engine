import json
from pathlib import Path

from src.paper_trading.safe_improved_recorded_data_paper_rerun_runner_scaffold_pack import (
    build_and_write_runner_scaffold_pack,
    build_runner_scaffold_report,
)


def _write_phase7_close_input(path: Path, *, accepted: bool = True) -> None:
    payload = {
        "status": "pass",
        "phase_7_complete": True,
        "accepted_for_future_safe_paper_rerun_runner_build": accepted,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_accepts_safe_phase7_close_and_locks_scaffold(tmp_path: Path) -> None:
    close_input = tmp_path / "phase7_close.json"
    _write_phase7_close_input(close_input)

    report = build_runner_scaffold_report(
        phase7_close_input_path=close_input,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.phase7_close_report_found is True
    assert report.phase7_complete is True
    assert report.phase7_accepts_runner_build is True
    assert report.accepted_for_future_runner_dry_run_pack is True
    assert report.runner_scaffold_built is True
    assert report.runner_execution_enabled is False
    assert report.scaffold_component_count == 6
    assert report.locked_component_count == 6
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_write_pack_outputs_manifest_and_components(tmp_path: Path) -> None:
    close_input = tmp_path / "phase7_close.json"
    output_dir = tmp_path / "pack"
    _write_phase7_close_input(close_input)

    report, outputs = build_and_write_runner_scaffold_pack(
        phase7_close_input_path=close_input,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "components_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "safe_improved_recorded_data_paper_rerun_runner_scaffold_pack"
    assert manifest["accepted_for_future_runner_dry_run_pack"] is True
    assert manifest["runner_scaffold_built"] is True
    assert manifest["runner_execution_enabled"] is False
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_phase7_close_stays_safe_and_does_not_accept_dry_run(tmp_path: Path) -> None:
    report = build_runner_scaffold_report(
        phase7_close_input_path=tmp_path / "missing_phase7_close.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.phase7_close_report_found is False
    assert report.accepted_for_future_runner_dry_run_pack is False
    assert report.runner_scaffold_built is True
    assert report.runner_execution_enabled is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "phase7_close_input_missing" for issue in report.issues)
