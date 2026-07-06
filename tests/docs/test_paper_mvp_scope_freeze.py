"""Tests for HQE Paper MVP v0.1 scope freeze docs."""

from pathlib import Path


SCOPE_DOC = Path("docs/PAPER_MVP_V0_1_SCOPE.md")
CHECKLIST_DOC = Path("docs/PAPER_MVP_RELEASE_CHECKLIST.md")
POLISH_DOC = Path("docs/DEFERRED_POLISH_BACKLOG.md")


def test_paper_mvp_scope_doc_freezes_paper_only_release():
    text = SCOPE_DOC.read_text(encoding="utf-8")

    assert "Paper MVP v0.1 is a paper-only release target." in text
    assert "It is not live trading." in text
    assert "It does not place broker orders." in text
    assert "It does not use real money." in text
    assert "It does not claim profitability." in text


def test_paper_mvp_scope_doc_lists_completed_paper_capabilities():
    text = SCOPE_DOC.read_text(encoding="utf-8")

    assert "Paper trading session" in text
    assert "Paper trading replay loop" in text
    assert "Paper replay journal persistence" in text
    assert "Paper replay journal index" in text
    assert "Friendly replay journal summary viewer" in text
    assert "Friendly replay journal runs viewer" in text


def test_paper_mvp_scope_doc_limits_remaining_blockers():
    text = SCOPE_DOC.read_text(encoding="utf-8")

    assert "Strategy-to-paper bridge" in text
    assert "Backtest evidence runner" in text
    assert "Paper MVP operator demo workflow" in text
    assert "Paper MVP release gate" in text
    assert "Git tag for the paper MVP release" in text


def test_paper_mvp_release_checklist_has_safety_and_operator_gates():
    text = CHECKLIST_DOC.read_text(encoding="utf-8")

    assert "No broker order placement in paper workflow." in text
    assert "No real-money trading." in text
    assert "Paper PnL labelled as simulation only." in text
    assert ".\\hqe_quick_check.bat" in text
    assert ".\\hqe_paper_replay_journal_all.bat" in text
    assert "v0.1-paper-mvp" in text


def test_deferred_polish_backlog_blocks_micro_polish_before_mvp():
    text = POLISH_DOC.read_text(encoding="utf-8")

    assert "Do not work on these items one by one before Paper MVP v0.1 is closed." in text
    assert "Polish must be bundled into a dedicated polish module" in text
    assert "Broken tests." in text
    assert "Any accidental broker/live-order path." in text


def test_readme_links_paper_mvp_scope_documents():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "Paper MVP v0.1 Scope Freeze" in text
    assert "docs/PAPER_MVP_V0_1_SCOPE.md" in text
    assert "docs/PAPER_MVP_RELEASE_CHECKLIST.md" in text
    assert "docs/DEFERRED_POLISH_BACKLOG.md" in text


def test_paper_mvp_scope_doc_marks_strategy_bridge_included_after_module_b():
    text = SCOPE_DOC.read_text(encoding="utf-8")

    included = text.split("## Included in Paper MVP v0.1", 1)[1].split("##", 1)[0]
    blockers = text.split("## Must Finish Before v0.1 Release", 1)[1].split("##", 1)[0]

    assert "Strategy-to-paper bridge" in included
    assert "Strategy-to-paper bridge" not in blockers


def test_paper_mvp_scope_doc_marks_backtest_evidence_included_after_module_c():
    text = SCOPE_DOC.read_text(encoding="utf-8")

    included = text.split("## Included in Paper MVP v0.1", 1)[1].split("##", 1)[0]
    blockers = text.split("## Must Finish Before v0.1 Release", 1)[1].split("##", 1)[0]

    assert "Backtest evidence runner" in included
    assert "Backtest evidence runner" not in blockers


def test_paper_mvp_scope_doc_marks_operator_workflow_included_after_module_d():
    text = SCOPE_DOC.read_text(encoding="utf-8")

    included = text.split("## Included in Paper MVP v0.1", 1)[1].split("##", 1)[0]
    blockers = text.split("## Must Finish Before v0.1 Release", 1)[1].split("##", 1)[0]

    assert "Paper MVP operator demo workflow" in included
    assert "Final paper operator guide" not in blockers


def test_paper_mvp_scope_doc_marks_release_gate_included_after_module_e():
    text = SCOPE_DOC.read_text(encoding="utf-8")

    included = text.split("## Included in Paper MVP v0.1", 1)[1].split("##", 1)[0]
    blockers = text.split("## Must Finish Before v0.1 Release", 1)[1].split("##", 1)[0]

    assert "Paper MVP release gate" in included
    assert "Release checklist pass" not in blockers
    assert "Git tag for the paper MVP release" in blockers
