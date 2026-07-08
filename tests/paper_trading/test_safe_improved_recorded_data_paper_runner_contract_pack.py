import json
from pathlib import Path

from src.paper_trading.safe_improved_recorded_data_paper_runner_contract_pack import (
    build_and_write_contract_pack,
    build_contract_report,
)


def _write_execution_plan(path: Path, *, safe: bool = True, accepted: bool = True) -> None:
    payload = {
        "status": "pass",
        "accepted_for_future_guarded_runner_module": accepted,
        "runner_execution_enabled": False,
        "backtest_executed": False,
        "optimization_executed": False,
        "strategy_logic_changed": False,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
    }
    if not safe:
        payload["runner_execution_enabled"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_contract_accepts_safe_execution_plan_and_locks_rules(tmp_path: Path) -> None:
    execution_plan = tmp_path / "execution_plan.json"
    _write_execution_plan(execution_plan)

    report = build_contract_report(
        execution_plan_input_path=execution_plan,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.execution_plan_found is True
    assert report.execution_plan_status == "pass"
    assert report.execution_plan_accepted_runner_contract is True
    assert report.accepted_for_future_guarded_paper_runner_execution is True
    assert report.contract_rule_count == 6
    assert report.locked_contract_rule_count == 6
    assert report.runner_mode == "contract_only"
    assert report.runner_execution_enabled is False
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_contract_writes_json_text_csv_and_manifest(tmp_path: Path) -> None:
    execution_plan = tmp_path / "execution_plan.json"
    output_dir = tmp_path / "pack"
    _write_execution_plan(execution_plan)

    report, outputs = build_and_write_contract_pack(
        execution_plan_input_path=execution_plan,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ("report_json", "report_txt", "rules_csv", "manifest_json"):
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "safe_improved_recorded_data_paper_runner_contract_pack"
    assert manifest["accepted_for_future_guarded_paper_runner_execution"] is True
    assert manifest["runner_mode"] == "contract_only"
    assert manifest["runner_execution_enabled"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["optimization_executed"] is False
    assert manifest["strategy_logic_changed"] is False
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False


def test_contract_rejects_unsafe_execution_plan_without_enabling_runner(tmp_path: Path) -> None:
    execution_plan = tmp_path / "execution_plan.json"
    _write_execution_plan(execution_plan, safe=False)

    report = build_contract_report(
        execution_plan_input_path=execution_plan,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted_for_future_guarded_paper_runner_execution is False
    assert report.runner_execution_enabled is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(
        issue["code"] == "unsafe_execution_plan_input_boundary"
        for issue in report.issues
    )
