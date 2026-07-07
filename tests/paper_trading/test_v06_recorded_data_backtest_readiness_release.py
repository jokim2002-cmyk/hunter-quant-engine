from pathlib import Path


RELEASE_DOC = Path("docs/V0_6_RECORDED_DATA_BACKTEST_READINESS_RELEASE.md")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v06_release_doc_exists_and_names_tag():
    text = _text(RELEASE_DOC)

    assert "v0.6 Recorded-Data Backtest Readiness Release" in text
    assert "v0.6-recorded-data-backtest-readiness" in text


def test_v06_release_doc_lists_backtest_readiness_chain():
    text = _text(RELEASE_DOC)

    assert "one-command paper backtest runner" in text
    assert "paper-only backtest acceptance gate" in text
    assert "paper-only backtest readiness gate" in text
    assert "paper backtest metrics engine" in text
    assert "paper backtest report writer" in text


def test_v06_release_doc_lists_required_shortcuts():
    text = _text(RELEASE_DOC)

    assert ".\\hqe_recorded_data_one_command_backtest_runner.bat" in text
    assert ".\\hqe_recorded_data_backtest_acceptance_gate.bat" in text
    assert ".\\hqe_recorded_data_backtest_readiness_gate.bat" in text
    assert ".\\hqe_recorded_data_backtest_metrics_engine.bat" in text
    assert ".\\hqe_recorded_data_backtest_report_writer.bat" in text


def test_v06_release_doc_preserves_option_buy_safety_contract():
    text = _text(RELEASE_DOC)

    assert "LONG = CE BUY paper plan only" in text
    assert "SHORT = PE BUY paper plan only" in text
    assert "NEUTRAL = no trade" in text
    assert "No option selling" in text
    assert "No broker orders" in text
    assert "No real money" in text


def test_v06_release_doc_rejects_profitability_claims():
    text = _text(RELEASE_DOC).lower()

    assert "no profitability claim" in text
    assert "profitability proof" in text
    assert "real-money trading" in text
    assert "live market data" in text


def test_v06_release_progress_metadata_is_present():
    text = _text(RELEASE_DOC)

    assert "Completed total before Module FFF: 57 modules" in text
    assert "v1.0 pending before Module FFF: 6 modules" in text
    assert "Completed total after Module FFF: 58 modules" in text
    assert "v1.0 pending after Module FFF: 5 modules" in text


def test_v06_release_expected_suite_count_is_present():
    text = _text(RELEASE_DOC)

    assert "Expected full quick-check suite after Module FFF: 2020 passed" in text


def test_v06_release_is_referenced_from_project_docs():
    readme = _text(Path("README.md"))
    roadmap = _text(Path("ROADMAP.md"))
    shortcuts = _text(Path("docs/HQE_SHORTCUTS.md"))

    combined = "\n".join([readme, roadmap, shortcuts])

    assert "v0.6-recorded-data-backtest-readiness" in combined
    assert "V0_6_RECORDED_DATA_BACKTEST_READINESS_RELEASE.md" in combined
    assert "hqe_recorded_data_backtest_readiness_gate.bat" in combined
    assert "not a profitability claim" in combined.lower()
