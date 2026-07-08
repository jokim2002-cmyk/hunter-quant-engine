import json
from pathlib import Path

from src.paper_trading.safe_improved_recorded_data_paper_rerun_runner_dry_run_validation_pack import (
    build_and_write_runner_dry_run_validation_pack,
    build_runner_dry_run_validation_report,
)


def _write_scaffold_input(path: Path, *, accepted: bool = True, runner_enabled: bool = False) -> None:
    payload = {
        "status": "pass",
        "accepted_for_future_runner_dry_run_pack": accepted,
        "runner_execution_enabled": runner_enabled,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_accepts_safe_scaffold_and_keeps_runner_disabled(tmp_path: Path) -> None:
    scaffold_input = tmp_path / "scaffold.json"
    _write_scaffold_input(scaffold_input)

    report = build_runner_dry_run_validation_report(
        scaffold_input_path=scaffold_input,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.scaffold_report_found is True
    assert report.scaffold_accepts_dry_run_pack is True
    assert report.scaffold_runner_execution_enabled is False
    assert report.failed_validation_count == 0
    assert report.accepted_for_future_runner_close_pack is True
    assert report.dry_run_validation_executed is True
    assert report.runner_execution_enabled is False
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_write_pack_outputs_manifest_and_validations(tmp_path: Path) -> None:
    scaffold_input = tmp_path / "scaffold.json"
    output_dir = tmp_path / "pack"
    _write_scaffold_input(scaffold_input)

    report, outputs = build_and_write_runner_dry_run_validation_pack(
        scaffold_input_path=scaffold_input,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "validations_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "safe_improved_recorded_data_paper_rerun_runner_dry_run_validation_pack"
    assert manifest["accepted_for_future_runner_close_pack"] is True
    assert manifest["dry_run_validation_executed"] is True
    assert manifest["runner_execution_enabled"] is False
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["strategy_logic_changed"] is False


def test_missing_scaffold_fails_validation_but_stays_safe(tmp_path: Path) -> None:
    report = build_runner_dry_run_validation_report(
        scaffold_input_path=tmp_path / "missing_scaffold.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.scaffold_report_found is False
    assert report.accepted_for_future_runner_close_pack is False
    assert report.runner_execution_enabled is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "scaffold_input_missing" for issue in report.issues)
