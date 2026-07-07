from pathlib import Path


RELEASE_DOC = Path("docs/V0_3_RECORDED_DATA_REPLAY_READINESS_RELEASE.md")
README = Path("README.md")
ROADMAP = Path("ROADMAP.md")

EXPECTED_SHORTCUTS = [
    "hqe_recorded_data_inventory.bat",
    "hqe_recorded_data_replay_dataset.bat",
    "hqe_recorded_data_replay_quality_gate.bat",
    "hqe_recorded_data_replay_dry_run.bat",
    "hqe_recorded_data_replay_evidence.bat",
    "hqe_recorded_data_replay_acceptance.bat",
    "hqe_recorded_data_replay_readiness.bat",
    "hqe_recorded_data_strategy_input_contract.bat",
    "hqe_recorded_data_strategy_replay_preflight.bat",
    "hqe_recorded_data_strategy_replay_scenario.bat",
    "hqe_recorded_data_strategy_replay_scenario_acceptance.bat",
    "hqe_recorded_data_strategy_replay_scenario_readiness.bat",
]


def _release_text() -> str:
    assert RELEASE_DOC.exists(), "Missing v0.3 release notes"
    return RELEASE_DOC.read_text(encoding="utf-8")


def test_v03_release_notes_exist_and_name_tag():
    text = _release_text()

    assert "v0.3 Recorded Data Replay Readiness Release" in text
    assert "v0.3-recorded-data-replay-readiness" in text


def test_v03_release_notes_include_all_recorded_data_shortcuts():
    text = _release_text()

    for shortcut in EXPECTED_SHORTCUTS:
        assert shortcut in text


def test_v03_release_notes_preserve_safety_boundary():
    text = _release_text().lower()

    assert "paper/simulation evidence only" in text
    assert "does not" in text
    assert "connect to a broker" in text
    assert "request live market data" in text
    assert "place real orders" in text
    assert "use real money" in text


def test_v03_release_notes_block_strategy_and_signal_execution_claims():
    text = _release_text().lower()

    assert "run strategies" in text
    assert "create signals" in text
    assert "create trade plans" in text


def test_v03_release_notes_are_not_profitability_claim():
    text = _release_text().lower()

    assert "not a profitability claim" in text
    assert "prove profitability" in text


def test_v03_release_notes_document_generated_outputs_are_ignored():
    text = _release_text().lower()

    assert "reports\\paper_trading" in text
    assert "remain ignored" in text
    assert "must not be committed" in text


def test_readme_mentions_v03_release():
    assert README.exists(), "Missing README.md"
    text = README.read_text(encoding="utf-8")

    assert "v0.3-recorded-data-replay-readiness" in text
    assert "hqe_recorded_data_strategy_replay_scenario_readiness.bat" in text


def test_roadmap_mentions_v03_release():
    assert ROADMAP.exists(), "Missing ROADMAP.md"
    text = ROADMAP.read_text(encoding="utf-8")

    assert "v0.3-recorded-data-replay-readiness" in text
    assert "Expected full quick-check suite after Module Z: 1676 passed" in text
