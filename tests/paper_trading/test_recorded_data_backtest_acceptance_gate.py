import json
from pathlib import Path

from src.paper_trading.recorded_data_backtest_acceptance_gate import (
    build_and_write_backtest_acceptance_report,
    build_backtest_acceptance_report,
    safety_notice,
)


STAGE_NAMES = [
    "strategy_replay_sandbox",
    "strategy_decision_audit",
    "strategy_decision_acceptance",
    "paper_option_trade_plan_simulator",
    "paper_fill_exit_simulator",
    "backtest_trade_ledger",
    "backtest_metrics_engine",
    "backtest_report_writer",
]


def _stages(status="pass", ready=True):
    return [
        {
            "stage_name": name,
            "status": status,
            "ready": ready,
            "output_directory": f"out/{name}",
            "primary_output": f"out/{name}/report.json",
            "detail": f"{name} status={status}, ready={ready}",
        }
        for name in STAGE_NAMES
    ]


def _runner(tmp_path, status="pass", ready=True, stages=None, final_outputs=True):
    final_report = tmp_path / "backtest_report.txt"
    final_metrics = tmp_path / "backtest_metrics.json"
    final_ledger = tmp_path / "backtest_trade_ledger.json"

    if final_outputs:
        final_report.write_text("paper report\nnot a profitability claim\n", encoding="utf-8")
        final_metrics.write_text("{}", encoding="utf-8")
        final_ledger.write_text("{}", encoding="utf-8")

    stages = _stages() if stages is None else stages

    return {
        "status": status,
        "ready_for_future_backtest_acceptance_gate": ready,
        "stage_count": len(stages),
        "passed_stage_count": sum(1 for stage in stages if stage["status"] == "pass"),
        "warning_stage_count": sum(1 for stage in stages if stage["status"] == "warn"),
        "failed_stage_count": sum(1 for stage in stages if stage["status"] == "fail"),
        "final_backtest_report_path": str(final_report),
        "final_metrics_path": str(final_metrics),
        "final_trade_ledger_path": str(final_ledger),
        "safety_notice": "paper/simulation one-command backtest runner only",
        "stages": stages,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_acceptance_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation backtest acceptance gate" in notice
    assert "recorded replay paper backtest evidence" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_runner_report_fails(tmp_path):
    report = build_backtest_acceptance_report(
        runner_report_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted_for_future_v1_testing_release_gate is False
    assert any(issue.code == "one_command_runner_report_missing" for issue in report.issues)


def test_valid_runner_report_is_accepted(tmp_path):
    runner = _write_json(tmp_path / "runner.json", _runner(tmp_path))

    report = build_backtest_acceptance_report(
        runner_report_path=runner,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.accepted_for_future_v1_testing_release_gate is True
    assert report.stage_count == 8
    assert report.passed_stage_count == 8
    assert report.failed_stage_count == 0
    assert report.final_backtest_report_path.endswith("backtest_report.txt")


def test_warning_runner_fails_by_default(tmp_path):
    runner = _write_json(
        tmp_path / "runner.json",
        _runner(tmp_path, status="warn", stages=_stages(status="warn", ready=True)),
    )

    report = build_backtest_acceptance_report(
        runner_report_path=runner,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "one_command_runner_warn" for issue in report.issues)


def test_warning_runner_can_remain_warning_when_allowed(tmp_path):
    runner = _write_json(
        tmp_path / "runner.json",
        _runner(tmp_path, status="warn", stages=_stages(status="warn", ready=True)),
    )

    report = build_backtest_acceptance_report(
        runner_report_path=runner,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted_for_future_v1_testing_release_gate is True


def test_not_ready_runner_fails(tmp_path):
    runner = _write_json(
        tmp_path / "runner.json",
        _runner(tmp_path, status="pass", ready=False),
    )

    report = build_backtest_acceptance_report(
        runner_report_path=runner,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "one_command_runner_not_ready" for issue in report.issues)


def test_missing_expected_stage_fails(tmp_path):
    stages = _stages()[:-1]
    runner = _write_json(tmp_path / "runner.json", _runner(tmp_path, stages=stages))

    report = build_backtest_acceptance_report(
        runner_report_path=runner,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_runner_stages" for issue in report.issues)
    assert any(issue.code == "runner_expected_stages_missing" for issue in report.issues)


def test_stage_not_ready_fails(tmp_path):
    stages = _stages()
    stages[0]["ready"] = False
    runner = _write_json(tmp_path / "runner.json", _runner(tmp_path, stages=stages))

    report = build_backtest_acceptance_report(
        runner_report_path=runner,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "runner_stage_not_ready" for issue in report.issues)


def test_missing_final_outputs_on_disk_fails(tmp_path):
    runner = _write_json(
        tmp_path / "runner.json",
        _runner(tmp_path, final_outputs=False),
    )

    report = build_backtest_acceptance_report(
        runner_report_path=runner,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "runner_final_outputs_missing_on_disk" for issue in report.issues)


def test_final_output_existence_check_can_be_skipped(tmp_path):
    runner = _write_json(
        tmp_path / "runner.json",
        _runner(tmp_path, final_outputs=False),
    )

    report = build_backtest_acceptance_report(
        runner_report_path=runner,
        output_dir=tmp_path / "out",
        require_final_outputs_exist=False,
    )

    assert report.status == "pass"
    assert report.accepted_for_future_v1_testing_release_gate is True


def test_build_and_write_outputs_and_docs_reference_acceptance_gate(tmp_path):
    runner = _write_json(tmp_path / "runner.json", _runner(tmp_path))

    report, outputs = build_and_write_backtest_acceptance_report(
        runner_report_path=runner,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["backtest_acceptance_gate_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_BACKTEST_ACCEPTANCE_GATE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["backtest_acceptance_gate_json"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["accepted_for_future_v1_testing_release_gate"] is True
    assert "hqe_recorded_data_backtest_acceptance_gate.bat" in combined_docs
    assert "paper-only backtest acceptance gate" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
