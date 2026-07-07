"""Tests for the live-readiness gate."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.live_readiness_gate import (
    LiveReadinessThresholds,
    build_live_readiness_report,
    format_live_readiness_report,
    live_readiness_report_to_dict,
    main,
    run_live_readiness_gate,
)


_GENERATED_AT = datetime(2026, 7, 6, 9, 15)


def _aggregate(
    *,
    passed=True,
    report_count=1,
    total_closed_trades=1,
    total_open_positions=0,
    total_unknown_trades=0,
    total_simulated_net_pnl=4535.0,
):
    return {
        "passed": passed,
        "paper_evidence_is_simulation_only": True,
        "report_count": report_count,
        "total_closed_trades": total_closed_trades,
        "total_open_positions": total_open_positions,
        "total_unknown_trades": total_unknown_trades,
        "total_simulated_net_pnl": total_simulated_net_pnl,
    }


def test_live_readiness_report_allows_engineering_with_good_aggregate():
    report = build_live_readiness_report(
        _aggregate(),
        generated_at=_GENERATED_AT,
    )

    assert report.live_readiness_allowed is True
    assert report.real_money_enabled is False
    assert report.broker_execution_enabled is False
    assert report.live_market_data_required is False
    assert report.not_a_profitability_claim is True
    assert report.blocking_reasons == ()


def test_live_readiness_report_blocks_missing_aggregate():
    report = build_live_readiness_report(
        None,
        evidence_aggregate_json="reports/paper_trading/evidence_aggregate/aggregate.json",
        generated_at=_GENERATED_AT,
    )

    assert report.live_readiness_allowed is False
    assert report.blocking_reasons
    assert "paper evidence aggregate missing" in report.blocking_reasons[0]
    assert "Run hqe_paper_mvp_operator_demo.bat" in report.blocking_reasons[0]


def test_live_readiness_report_blocks_failed_aggregate():
    report = build_live_readiness_report(
        _aggregate(passed=False),
        generated_at=_GENERATED_AT,
    )

    assert report.live_readiness_allowed is False
    assert "paper evidence aggregate failed its gates" in report.blocking_reasons


def test_live_readiness_report_blocks_custom_net_pnl_threshold():
    report = build_live_readiness_report(
        _aggregate(total_simulated_net_pnl=100.0),
        thresholds=LiveReadinessThresholds(min_total_simulated_net_pnl=500.0),
        generated_at=_GENERATED_AT,
    )

    assert report.live_readiness_allowed is False
    assert "simulated net pnl below minimum: 100.0 < 500.0" in report.blocking_reasons


def test_live_readiness_gate_writes_outputs_under_reports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_required_safety_docs(tmp_path)

    aggregate_path = tmp_path / "reports" / "paper_trading" / "evidence_aggregate" / "aggregate.json"
    aggregate_path.parent.mkdir(parents=True)
    aggregate_path.write_text(json.dumps(_aggregate()), encoding="utf-8")

    report, paths = run_live_readiness_gate(
        aggregate_path,
        output_dir=tmp_path / "reports" / "paper_trading" / "live_readiness",
        generated_at=_GENERATED_AT,
    )

    assert report.live_readiness_allowed is True
    assert paths.readiness_json.exists()
    assert paths.readiness_text.exists()
    assert paths.manifest_json.exists()


def test_live_readiness_report_dict_is_json_safe():
    report = build_live_readiness_report(
        _aggregate(),
        generated_at=_GENERATED_AT,
    )

    payload = live_readiness_report_to_dict(report)

    assert payload["live_readiness_allowed"] is True
    assert payload["real_money_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["blocking_reasons"] == []


def test_live_readiness_format_is_trader_friendly():
    report = build_live_readiness_report(
        _aggregate(),
        generated_at=_GENERATED_AT,
    )

    text = format_live_readiness_report(report)

    assert "Hunter Quant Engine - Live Readiness Gate" in text
    assert "live-readiness engineering check only" in text
    assert "real money disabled" in text
    assert "broker execution disabled" in text
    assert "not a profitability claim" in text
    assert "live-readiness allowed: True" in text


def test_live_readiness_gate_rejects_output_outside_reports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_required_safety_docs(tmp_path)

    aggregate_path = tmp_path / "reports" / "paper_trading" / "evidence_aggregate" / "aggregate.json"
    aggregate_path.parent.mkdir(parents=True)
    aggregate_path.write_text(json.dumps(_aggregate()), encoding="utf-8")

    with pytest.raises(ValueError, match="reports/"):
        run_live_readiness_gate(
            aggregate_path,
            output_dir=tmp_path / "live_readiness",
        )


def test_live_readiness_main_handles_missing_default(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert main() == 1

    out = capsys.readouterr().out

    assert "Live Readiness Gate" in out
    assert "live-readiness allowed: False" in out
    assert "paper evidence aggregate missing" in out


def test_live_readiness_shortcut_points_to_safe_cli():
    text = Path("hqe_live_readiness_check.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.live_readiness_gate" in text
    assert ".venv\\scripts\\python.exe" in text
    assert "does not enable real money" in text
    assert "broker execution" in text


def test_live_readiness_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/live_readiness_gate.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_live_readiness_docs_define_boundary():
    text = Path("docs/LIVE_READINESS_GATE.md").read_text(encoding="utf-8")

    assert "It is not live trading." in text
    assert "It does not enable real money." in text
    assert "It does not enable broker execution." in text
    assert "It does not claim profitability." in text
    assert ".\\hqe_live_readiness_check.bat" in text


def _write_required_safety_docs(root: Path):
    docs = root / "docs"
    docs.mkdir(parents=True)
    safety_text = "\n".join(
        [
            "It does not place broker orders.",
            "It does not use real money.",
            "It does not claim profitability.",
            "Live trading remains deferred",
        ]
    )

    for name in (
        "PAPER_MVP_V0_1_SCOPE.md",
        "PAPER_OPERATOR_GUIDE.md",
        "PAPER_MVP_V0_1_RELEASE_NOTES.md",
    ):
        (docs / name).write_text(safety_text, encoding="utf-8")
