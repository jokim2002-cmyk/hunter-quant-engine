import json
from pathlib import Path

from src.paper_trading.recorded_data_strategy_replay_sandbox import (
    build_and_write_strategy_replay_sandbox_report,
    build_strategy_replay_sandbox_report,
    safety_notice,
)


def _readiness(status="pass", ready=True):
    return {
        "status": status,
        "ready_for_future_consumer_evidence_release": ready,
    }


def _bar(close=101.5):
    return {
        "source_path": "sample.csv",
        "source_type": "csv",
        "source_row_number": 1,
        "timestamp": "2026-01-01T09:15:00+05:30",
        "open": 100.0,
        "high": 102.0,
        "low": 99.5,
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
        bars or [_bar()],
    )
    return readiness_path, bars_path


def test_safety_notice_preserves_strategy_replay_sandbox_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not generate signals" in notice
    assert "create trade plans" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_consumer_evidence_readiness_fails(tmp_path):
    _, bars = _inputs(tmp_path)

    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=tmp_path / "missing.json",
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "consumer_evidence_readiness_missing" for issue in report.issues)


def test_missing_strategy_input_bars_fails(tmp_path):
    readiness, _ = _inputs(tmp_path)

    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=readiness,
        strategy_input_bars_path=tmp_path / "missing.jsonl",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_input_bars_missing" for issue in report.issues)


def test_valid_inputs_create_sandbox_event(tmp_path):
    readiness, bars = _inputs(tmp_path)

    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=readiness,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_strategy_decision_audit is True
    assert report.input_bar_count == 1
    assert report.sandbox_event_count == 1
    assert report.sandbox_events[0].event_type == "strategy_replay_bar_available"
    assert report.sandbox_events[0].signal_mode == "signals_not_generated"


def test_warning_readiness_fails_by_default(tmp_path):
    readiness, bars = _inputs(tmp_path, readiness=_readiness(status="warn", ready=True))

    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=readiness,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "consumer_evidence_readiness_warn" for issue in report.issues)


def test_warning_readiness_can_remain_warning_when_allowed(tmp_path):
    readiness, bars = _inputs(tmp_path, readiness=_readiness(status="warn", ready=True))

    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=readiness,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_strategy_decision_audit is True


def test_min_bars_rule_can_fail(tmp_path):
    readiness, bars = _inputs(tmp_path)

    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=readiness,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
        min_bars=2,
    )

    assert report.status == "fail"
    assert any(
        issue.code == "insufficient_strategy_replay_sandbox_bars"
        for issue in report.issues
    )


def test_bar_missing_required_fields_fails(tmp_path):
    bad_bar = _bar()
    bad_bar.pop("close")
    readiness, bars = _inputs(tmp_path, bars=[bad_bar])

    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=readiness,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.sandbox_event_count == 0
    assert any(
        issue.code == "strategy_input_bar_missing_required_fields"
        for issue in report.issues
    )


def test_bar_wrong_modes_fails(tmp_path):
    bad_bar = _bar()
    bad_bar["execution_mode"] = "live"
    readiness, bars = _inputs(tmp_path, bars=[bad_bar])

    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=readiness,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_input_bar_wrong_modes" for issue in report.issues)


def test_forbidden_bar_fields_fail(tmp_path):
    bad_bar = _bar()
    bad_bar["order_id"] = "not-allowed"
    readiness, bars = _inputs(tmp_path, bars=[bad_bar])

    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=readiness,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_input_bar_forbidden_fields" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_sandbox(tmp_path):
    readiness, bars = _inputs(tmp_path)

    report, outputs = build_and_write_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=readiness,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["strategy_replay_sandbox_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_STRATEGY_REPLAY_SANDBOX.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["strategy_replay_sandbox_json"].exists()
    assert outputs["strategy_replay_sandbox_events_jsonl"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_strategy_decision_audit"] is True
    assert "hqe_recorded_data_strategy_replay_sandbox.bat" in combined_docs
    assert "paper/simulation" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
