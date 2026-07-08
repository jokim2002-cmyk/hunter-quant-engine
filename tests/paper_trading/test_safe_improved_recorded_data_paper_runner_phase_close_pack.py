import json
from pathlib import Path

from src.paper_trading.safe_improved_recorded_data_paper_runner_phase_close_pack import (
    build_and_write_phase_close_pack,
    build_phase_close_report,
)


def _write_contract(path: Path, *, safe: bool = True, accepted: bool = True) -> None:
    payload = {
        "status": "pass",
        "accepted_for_future_guarded_paper_runner_execution": accepted,
        "runner_execution_enabled": False,
        "backtest_executed": False,
        "optimization_executed": False,
        "strategy_logic_changed": False,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
    }
    if not safe:
        payload["profitability_claim_allowed"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_phase_close_accepts_safe_contract_and_closes_phase9(tmp_path: Path) -> None:
    contract = tmp_path / "contract.json"
    _write_contract(contract)

    report = build_phase_close_report(
        contract_input_path=contract,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.contract_report_found is True
    assert report.contract_report_status == "pass"
    assert report.contract_accepts_future_runner_execution is True
    assert report.phase_9_complete is True
    assert report.accepted_for_future_phase10_safe_paper_runner_review is True
    assert report.checklist_item_count == 6
    assert report.passed_checklist_item_count == 6
    assert report.runner_execution_enabled is False
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_phase_close_writes_json_text_csv_and_manifest(tmp_path: Path) -> None:
    contract = tmp_path / "contract.json"
    output_dir = tmp_path / "pack"
    _write_contract(contract)

    report, outputs = build_and_write_phase_close_pack(
        contract_input_path=contract,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ("report_json", "report_txt", "checklist_csv", "manifest_json"):
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "safe_improved_recorded_data_paper_runner_phase_close_pack"
    assert manifest["phase_9_complete"] is True
    assert manifest["accepted_for_future_phase10_safe_paper_runner_review"] is True
    assert manifest["runner_execution_enabled"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["optimization_executed"] is False
    assert manifest["strategy_logic_changed"] is False
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False


def test_phase_close_rejects_unsafe_contract_without_live_or_profit_claim(tmp_path: Path) -> None:
    contract = tmp_path / "contract.json"
    _write_contract(contract, safe=False)

    report = build_phase_close_report(
        contract_input_path=contract,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.phase_9_complete is False
    assert report.accepted_for_future_phase10_safe_paper_runner_review is False
    assert report.runner_execution_enabled is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "unsafe_contract_input_boundary" for issue in report.issues)
