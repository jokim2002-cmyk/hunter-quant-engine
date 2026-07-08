import json
from pathlib import Path

from src.paper_trading.safe_paper_runner_review_readiness_pack import (
    build_and_write_review_readiness_pack,
    build_review_readiness_report,
)


def _write_phase9_close(path: Path, *, safe: bool = True, complete: bool = True) -> None:
    payload = {
        "status": "pass",
        "phase_9_complete": complete,
        "accepted_for_future_phase10_safe_paper_runner_review": True,
        "runner_execution_enabled": False,
        "backtest_executed": False,
        "optimization_executed": False,
        "strategy_logic_changed": False,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
    }
    if not safe:
        payload["ready_for_live_or_real_money"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_review_readiness_accepts_safe_phase9_close_and_starts_phase10(tmp_path: Path) -> None:
    phase9_close = tmp_path / "phase9_close.json"
    _write_phase9_close(phase9_close)

    report = build_review_readiness_report(
        phase9_close_input_path=phase9_close,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.phase9_close_report_found is True
    assert report.phase9_close_status == "pass"
    assert report.phase9_complete is True
    assert report.phase9_accepts_phase10_review is True
    assert report.phase10_started is True
    assert report.accepted_for_future_safe_paper_runner_review_module is True
    assert report.readiness_item_count == 6
    assert report.passed_readiness_item_count == 6
    assert report.review_mode == "review_readiness_only"
    assert report.runner_execution_enabled is False
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_review_readiness_writes_json_text_csv_and_manifest(tmp_path: Path) -> None:
    phase9_close = tmp_path / "phase9_close.json"
    output_dir = tmp_path / "pack"
    _write_phase9_close(phase9_close)

    report, outputs = build_and_write_review_readiness_pack(
        phase9_close_input_path=phase9_close,
        output_dir=output_dir,
    )

    assert report.status == "pass"
    for key in ("report_json", "report_txt", "readiness_csv", "manifest_json"):
        assert Path(outputs[key]).exists()

    manifest = json.loads(Path(outputs["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["report_type"] == "safe_paper_runner_review_readiness_pack"
    assert manifest["phase10_started"] is True
    assert manifest["accepted_for_future_safe_paper_runner_review_module"] is True
    assert manifest["review_mode"] == "review_readiness_only"
    assert manifest["runner_execution_enabled"] is False
    assert manifest["backtest_executed"] is False
    assert manifest["optimization_executed"] is False
    assert manifest["strategy_logic_changed"] is False
    assert manifest["ready_for_live_or_real_money"] is False
    assert manifest["profitability_claim_allowed"] is False


def test_review_readiness_rejects_unsafe_phase9_close_without_live_readiness(tmp_path: Path) -> None:
    phase9_close = tmp_path / "phase9_close.json"
    _write_phase9_close(phase9_close, safe=False)

    report = build_review_readiness_report(
        phase9_close_input_path=phase9_close,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.phase10_started is False
    assert report.accepted_for_future_safe_paper_runner_review_module is False
    assert report.runner_execution_enabled is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert any(issue["code"] == "unsafe_phase9_close_input_boundary" for issue in report.issues)
