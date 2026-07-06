"""
Paper MVP Release Gate Tests

Release readiness only. No broker. No live market data. No real orders.
"""

from datetime import datetime
from pathlib import Path

from src.paper_trading.paper_mvp_release_gate import (
    format_paper_mvp_release_gate_report,
    main,
    run_paper_mvp_release_gate,
)


_GENERATED_AT = datetime(2026, 7, 6, 9, 15)


def test_paper_mvp_release_gate_passes_current_repo():
    report = run_paper_mvp_release_gate(generated_at=_GENERATED_AT)

    assert report.passed is True
    assert report.release_name == "v0.1-paper-mvp"
    assert report.paper_only is True
    assert report.no_broker_orders is True
    assert report.no_live_market_data is True
    assert report.no_real_orders is True
    assert report.not_a_profitability_claim is True
    assert report.blocking_reasons == ()


def test_paper_mvp_release_gate_format_is_trader_friendly():
    report = run_paper_mvp_release_gate(generated_at=_GENERATED_AT)

    text = format_paper_mvp_release_gate_report(report)

    assert "Hunter Quant Engine - Paper MVP Release Gate" in text
    assert "paper-only release readiness check" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "not a profitability claim" in text
    assert "release name: v0.1-paper-mvp" in text
    assert "passed gates: True" in text
    assert "PASS: required file: README.md" in text


def test_paper_mvp_release_gate_blocks_missing_required_files(tmp_path):
    report = run_paper_mvp_release_gate(tmp_path, generated_at=_GENERATED_AT)

    assert report.passed is False
    assert any("missing: README.md" in reason for reason in report.blocking_reasons)


def test_paper_mvp_release_gate_blocks_missing_required_text(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "PAPER_MVP_V0_1_SCOPE.md").write_text(
        "Paper MVP v0.1 is a paper-only release target.",
        encoding="utf-8",
    )

    report = run_paper_mvp_release_gate(tmp_path, generated_at=_GENERATED_AT)

    assert report.passed is False
    assert any("missing text:" in reason for reason in report.blocking_reasons)


def test_paper_mvp_release_gate_main_prints_success(capsys):
    assert main() == 0

    out = capsys.readouterr().out

    assert "Paper MVP Release Gate" in out
    assert "passed gates: True" in out
    assert "Tag" not in out


def test_paper_mvp_release_check_shortcut_points_to_safe_cli():
    text = Path("hqe_paper_mvp_release_check.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.paper_mvp_release_gate" in text
    assert ".venv\scripts\python.exe" in text
    assert "no tag is created" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text


def test_paper_mvp_release_gate_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_mvp_release_gate.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_paper_mvp_release_gate_does_not_create_tag():
    source = Path("src/paper_trading/paper_mvp_release_gate.py").read_text(
        encoding="utf-8"
    ).lower()
    shortcut = Path("hqe_paper_mvp_release_check.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "git tag" not in source
    assert "git tag" not in shortcut
    assert "tag creation is still manual" in shortcut
