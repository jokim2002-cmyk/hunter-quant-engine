from pathlib import Path


RELEASE_DOC = Path("docs/V0_5_PAPER_STRATEGY_ADAPTER_CONSUMER_EVIDENCE_READINESS_RELEASE.md")
README = Path("README.md")
ROADMAP = Path("ROADMAP.md")
SHORTCUTS = Path("docs/HQE_SHORTCUTS.md")

TAG = "v0.5-paper-strategy-adapter-consumer-evidence-readiness"
MAIN_COMMAND = "hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness.bat"


def _text(path: Path) -> str:
    assert path.exists(), f"Missing expected file: {path}"
    return path.read_text(encoding="utf-8")


def test_v05_release_doc_exists_and_names_tag():
    text = _text(RELEASE_DOC)

    assert "v0.5 Paper Strategy Adapter Consumer Evidence Readiness Release" in text
    assert TAG in text


def test_v05_release_doc_names_main_command_and_output():
    text = _text(RELEASE_DOC)

    assert MAIN_COMMAND in text
    assert "reports\\paper_trading\\recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness" in text


def test_v05_release_doc_lists_consumer_evidence_modules():
    text = _text(RELEASE_DOC)

    required_modules = [
        "Module NN",
        "Module OO",
        "Module PP",
        "Module QQ",
        "Module RR",
        "Module SS",
        "Module TT",
    ]

    for module_name in required_modules:
        assert module_name in text


def test_v05_release_doc_preserves_safety_boundary():
    text = _text(RELEASE_DOC).lower()

    assert "paper/simulation evidence only" in text
    assert "does not execute strategy logic" in text
    assert "create signals" in text
    assert "calculate pnl" in text
    assert "prove profitability" in text


def test_v05_release_doc_preserves_trading_boundary():
    text = _text(RELEASE_DOC).lower()

    assert "nifty option-buy only" in text
    assert "long means ce buy plan" in text
    assert "short means pe buy plan" in text
    assert "neutral means no trade" in text
    assert "no option selling" in text
    assert "no short ce/pe" in text


def test_v05_release_doc_mentions_ignored_reports_and_no_profitability_claim():
    text = _text(RELEASE_DOC).lower()

    assert "reports\\paper_trading remain ignored" in text
    assert "must not be committed" in text
    assert "not a profitability claim" in text


def test_v05_readme_and_roadmap_reference_release():
    combined = _text(README) + "\n" + _text(ROADMAP)

    assert TAG in combined
    assert MAIN_COMMAND in combined
    assert "1891 passed" in combined
    assert "v1.0 Testing Edition" in combined


def test_v05_shortcuts_reference_release_command():
    text = _text(SHORTCUTS)

    assert TAG in text
    assert MAIN_COMMAND in text
    assert "not a profitability claim" in text.lower()
