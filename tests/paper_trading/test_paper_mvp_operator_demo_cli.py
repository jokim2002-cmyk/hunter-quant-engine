"""
Paper MVP Operator Demo CLI Tests

Paper/simulation only. No broker. No live market data. No real orders.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.paper_mvp_operator_demo_cli import (
    format_paper_mvp_operator_demo_result,
    main,
    run_paper_mvp_operator_demo,
)


_GENERATED_AT = datetime(2026, 7, 6, 9, 15)


def test_paper_mvp_operator_demo_runs_full_paper_workflow(tmp_path):
    result = run_paper_mvp_operator_demo(
        output_dir=tmp_path / "reports" / "paper_trading" / "operator_demo",
        generated_at=_GENERATED_AT,
    )

    assert result.bridge_result.submitted_orders_count == 1
    assert result.bridge_result.skipped_plans_count == 0
    assert result.bridge_result.exit_records_count == 1
    assert result.bridge_result.summary.open_positions_count == 0
    assert result.bridge_result.summary.closed_trades_count == 1
    assert result.evidence_report.passed is True
    assert result.evidence_report.closed_trades == 1
    assert result.evidence_report.open_positions == 0


def test_paper_mvp_operator_demo_writes_report_and_evidence_files(tmp_path):
    result = run_paper_mvp_operator_demo(
        output_dir=tmp_path / "reports" / "paper_trading" / "operator_demo",
        generated_at=_GENERATED_AT,
    )

    assert result.bridge_result.report_paths.report_text.exists()
    assert result.bridge_result.report_paths.summary_json.exists()
    assert result.bridge_result.report_paths.orders_json.exists()
    assert result.evidence_paths.evidence_text.exists()
    assert result.evidence_paths.evidence_json.exists()
    assert result.evidence_paths.manifest_json.exists()


def test_paper_mvp_operator_demo_format_is_trader_friendly(tmp_path):
    result = run_paper_mvp_operator_demo(
        output_dir=tmp_path / "reports" / "paper_trading" / "operator_demo",
        generated_at=_GENERATED_AT,
    )

    text = format_paper_mvp_operator_demo_result(result)

    assert "Hunter Quant Engine - Paper MVP Operator Demo" in text
    assert "paper/simulation only" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "not a profitability claim" in text
    assert "submitted orders: 1" in text
    assert "closed trades: 1" in text
    assert "passed gates: True" in text
    assert "paper report:" in text
    assert "evidence json:" in text


def test_paper_mvp_operator_demo_main_prints_success_output(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert main() == 0

    out = capsys.readouterr().out

    assert "Paper MVP Operator Demo" in out
    assert "passed gates: True" in out
    assert "no real orders" in out


def test_paper_mvp_operator_demo_rejects_output_outside_reports(tmp_path):
    with pytest.raises(ValueError, match="reports/"):
        run_paper_mvp_operator_demo(output_dir=tmp_path / "operator_demo")


def test_paper_mvp_operator_demo_shortcut_points_to_safe_cli():
    text = Path("hqe_paper_mvp_operator_demo.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.paper_mvp_operator_demo_cli" in text
    assert ".venv\scripts\python.exe" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "paper pnl is simulation only" in text


def test_paper_mvp_operator_demo_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_mvp_operator_demo_cli.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
