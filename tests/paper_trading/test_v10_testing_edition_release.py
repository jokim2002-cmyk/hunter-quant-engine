from pathlib import Path


RELEASE_DOC = Path("docs/V1_0_TESTING_EDITION_RELEASE.md")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v10_release_doc_exists_and_names_tag():
    text = _text(RELEASE_DOC)

    assert "v1.0 Testing Edition Release" in text
    assert "v1.0-testing-edition" in text


def test_v10_release_doc_lists_final_gate_chain():
    text = _text(RELEASE_DOC)

    assert "paper-only backtest readiness gate" in text
    assert "v1.0 Testing Edition release gate" in text
    assert "v1.0 Testing Edition operator handoff pack" in text
    assert "v1.0 Testing Edition release notes pack" in text
    assert "v1.0 Testing Edition release candidate gate" in text


def test_v10_release_doc_lists_final_operator_shortcuts():
    text = _text(RELEASE_DOC)

    assert ".\\hqe_recorded_data_backtest_readiness_gate.bat" in text
    assert ".\\hqe_v1_testing_release_gate.bat" in text
    assert ".\\hqe_v1_testing_operator_handoff_pack.bat" in text
    assert ".\\hqe_v1_testing_release_notes.bat" in text
    assert ".\\hqe_v1_testing_release_candidate_gate.bat" in text


def test_v10_release_doc_preserves_option_buy_safety_contract():
    text = _text(RELEASE_DOC)

    assert "LONG = CE BUY paper plan only" in text
    assert "SHORT = PE BUY paper plan only" in text
    assert "NEUTRAL = no trade" in text
    assert "No option selling" in text
    assert "No broker orders" in text
    assert "No real money" in text


def test_v10_release_doc_rejects_profitability_and_live_execution_claims():
    text = _text(RELEASE_DOC).lower()

    assert "does not prove profitability" in text
    assert "does not represent live broker pnl" in text
    assert "does not place real orders" in text
    assert "does not use real money" in text
    assert "does not connect to fyers or any broker" in text
    assert "does not depend on live market data" in text


def test_v10_release_progress_metadata_is_present():
    text = _text(RELEASE_DOC)

    assert "Completed total before Module KKK: 62 modules" in text
    assert "v1.0 pending before Module KKK: 1 module" in text
    assert "Completed total after Module KKK: 63 modules" in text
    assert "v1.0 pending after Module KKK: 0 modules" in text


def test_v10_release_expected_suite_count_is_present():
    text = _text(RELEASE_DOC)

    assert "Expected full quick-check suite after Module KKK: 2072 passed" in text


def test_v10_release_is_referenced_from_project_docs():
    readme = _text(Path("README.md"))
    roadmap = _text(Path("ROADMAP.md"))
    shortcuts = _text(Path("docs/HQE_SHORTCUTS.md"))

    combined = "\n".join([readme, roadmap, shortcuts])

    assert "v1.0-testing-edition" in combined
    assert "V1_0_TESTING_EDITION_RELEASE.md" in combined
    assert "hqe_v1_testing_release_candidate_gate.bat" in combined
    assert "not a profitability claim" in combined.lower()
