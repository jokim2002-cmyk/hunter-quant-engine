import json
from pathlib import Path

from src.paper_trading.recorded_data_one_command_backtest_runner import (
    build_and_write_one_command_backtest_runner_report,
    safety_notice,
)


def _readiness(status="pass", ready=True):
    return {
        "status": status,
        "ready_for_future_consumer_evidence_release": ready,
    }


def _bar(row, close):
    return {
        "source_path": "sample.csv",
        "source_type": "csv",
        "source_row_number": row,
        "timestamp": f"2026-01-01T09:{14 + row:02d}:00+05:30",
        "open": close - 1,
        "high": close + 1,
        "low": close - 2,
        "close": close,
        "volume": 1000,
        "data_mode": "recorded_replay",
        "execution_mode": "paper_simulation_only",
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_jsonl(path, rows):
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _inputs(tmp_path, readiness=None, bars=None):
    readiness_path = _write_json(
        tmp_path / "consumer_evidence_readiness.json",
        readiness or _readiness(),
    )
    bars_path = _write_jsonl(
        tmp_path / "strategy_input_bars.jsonl",
        bars
        or [
            _bar(1, 100.0),
            _bar(2, 102.0),
            _bar(3, 101.0),
            _bar(4, 103.0),
            _bar(5, 102.0),
        ],
    )
    return readiness_path, bars_path


def _run(tmp_path, readiness=None, bars=None, **kwargs):
    readiness_path, bars_path = _inputs(tmp_path, readiness=readiness, bars=bars)
    base = tmp_path / "stages"
    return build_and_write_one_command_backtest_runner_report(
        consumer_evidence_readiness_path=readiness_path,
        strategy_input_bars_path=bars_path,
        output_dir=tmp_path / "runner",
        sandbox_output_dir=base / "sandbox",
        decision_audit_output_dir=base / "decision_audit",
        decision_acceptance_output_dir=base / "decision_acceptance",
        trade_plan_output_dir=base / "trade_plan",
        fill_exit_output_dir=base / "fill_exit",
        trade_ledger_output_dir=base / "ledger",
        metrics_output_dir=base / "metrics",
        report_writer_output_dir=base / "report_writer",
        min_bars=kwargs.pop("min_bars", 1),
        min_decisions=kwargs.pop("min_decisions", 1),
        min_non_neutral_decisions=kwargs.pop("min_non_neutral_decisions", 0),
        min_plans=kwargs.pop("min_plans", 1),
        min_lifecycles=kwargs.pop("min_lifecycles", 1),
        min_trades=kwargs.pop("min_trades", 1),
        threshold_points=kwargs.pop("threshold_points", 0.0),
        starting_equity_reference=kwargs.pop("starting_equity_reference", 100000.0),
        allow_warnings=kwargs.pop("allow_warnings", False),
        max_bars=kwargs.pop("max_bars", None),
    )


def test_safety_notice_preserves_one_command_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation one-command backtest runner" in notice
    assert "ce/pe option-buy" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_valid_inputs_run_all_backtest_stages(tmp_path):
    report, outputs = _run(tmp_path, min_trades=1)

    stage_names = [stage.stage_name for stage in report.stages]

    assert report.status == "pass"
    assert report.ready_for_future_backtest_acceptance_gate is True
    assert report.stage_count == 8
    assert report.passed_stage_count == 8
    assert report.failed_stage_count == 0
    assert "strategy_replay_sandbox" in stage_names
    assert "backtest_report_writer" in stage_names
    assert Path(report.final_backtest_report_path).exists()
    assert Path(report.final_metrics_path).exists()
    assert Path(report.final_trade_ledger_path).exists()
    assert outputs["one_command_backtest_runner_json"].exists()


def test_missing_readiness_file_fails_but_writes_runner_report(tmp_path):
    _, bars_path = _inputs(tmp_path)
    base = tmp_path / "stages"

    report, outputs = build_and_write_one_command_backtest_runner_report(
        consumer_evidence_readiness_path=tmp_path / "missing.json",
        strategy_input_bars_path=bars_path,
        output_dir=tmp_path / "runner",
        sandbox_output_dir=base / "sandbox",
        decision_audit_output_dir=base / "decision_audit",
        decision_acceptance_output_dir=base / "decision_acceptance",
        trade_plan_output_dir=base / "trade_plan",
        fill_exit_output_dir=base / "fill_exit",
        trade_ledger_output_dir=base / "ledger",
        metrics_output_dir=base / "metrics",
        report_writer_output_dir=base / "report_writer",
    )

    assert report.status == "fail"
    assert report.ready_for_future_backtest_acceptance_gate is False
    assert outputs["one_command_backtest_runner_json"].exists()


def test_warning_readiness_fails_by_default(tmp_path):
    report, _ = _run(
        tmp_path,
        readiness=_readiness(status="warn", ready=True),
    )

    assert report.status == "fail"
    assert any(stage.status == "fail" for stage in report.stages)


def test_warning_readiness_can_remain_warning_when_allowed(tmp_path):
    report, _ = _run(
        tmp_path,
        readiness=_readiness(status="warn", ready=True),
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_backtest_acceptance_gate is True
    assert any(stage.status == "warn" for stage in report.stages)


def test_min_bars_rule_can_fail(tmp_path):
    report, _ = _run(
        tmp_path,
        bars=[_bar(1, 100.0)],
        min_bars=2,
    )

    assert report.status == "fail"
    assert any(stage.stage_name == "strategy_replay_sandbox" for stage in report.stages)


def test_min_non_neutral_decisions_rule_can_fail(tmp_path):
    report, _ = _run(
        tmp_path,
        bars=[_bar(1, 100.0), _bar(2, 100.0), _bar(3, 100.0)],
        min_non_neutral_decisions=1,
        min_plans=0,
        min_lifecycles=0,
        min_trades=0,
    )

    assert report.status == "fail"
    assert any(stage.stage_name == "strategy_decision_acceptance" for stage in report.stages)


def test_runner_respects_max_bars_limit(tmp_path):
    report, _ = _run(
        tmp_path,
        max_bars=2,
        min_trades=0,
    )

    assert report.stage_count == 8
    assert report.status in {"pass", "warn", "fail"}


def test_runner_report_outputs_include_safety_text(tmp_path):
    report, outputs = _run(tmp_path, min_trades=1)

    text = outputs["one_command_backtest_runner_txt"].read_text(encoding="utf-8").lower()
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert "long = ce buy paper plan only" in text
    assert "short = pe buy paper plan only" in text
    assert "no real money" in text
    assert "not a profitability claim" in text
    assert manifest["ready_for_future_backtest_acceptance_gate"] is True


def test_docs_reference_one_command_runner():
    doc_paths = [
        Path("docs/RECORDED_DATA_ONE_COMMAND_BACKTEST_RUNNER.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_recorded_data_one_command_backtest_runner.bat" in combined_docs
    assert "one-command paper backtest" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()


def test_runner_progress_metadata_in_docs():
    doc = Path("docs/RECORDED_DATA_ONE_COMMAND_BACKTEST_RUNNER.md").read_text(encoding="utf-8")

    assert "Completed total before Module CCC: 54 modules" in doc
    assert "v1.0 pending before Module CCC: 9 modules" in doc
    assert "v1.0 pending after Module CCC: 8 modules" in doc
