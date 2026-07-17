from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "scripts" / "hqe_product_app_v2.py"
CENTER = ROOT / "scripts" / "hqe_app_strategy_pack_center.py"
WORKFLOW = ROOT / "src" / "multi_strategy" / "import_workflow.py"


def test_strategy_pack_center_exposes_reviewed_workflow_wrappers():
    text = CENTER.read_text(encoding="utf-8")
    for name in (
        "reviewed_import_snapshot",
        "begin_reviewed_package_import",
        "approve_reviewed_package_import",
        "install_reviewed_package_metadata",
        "multi_strategy_phase6_reviewed_import",
    ):
        assert name in text
    assert text.index("REPO_ROOT =") < text.index(
        "from src.multi_strategy.import_workflow import"
    )


def test_product_app_wires_complete_reviewed_import_dialog():
    text = APP.read_text(encoding="utf-8")
    for value in (
        "Reviewed Package Import",
        "Reviewed Strategy Package Import",
        "Choose & Quarantine Package",
        "Explicitly Approve Metadata Import",
        "Install Approved Metadata",
        "APPROVE REVIEWED METADATA IMPORT",
        "METADATA CATALOG ONLY",
    ):
        assert value in text
    assert "multi_strategy_phase6_reviewed_import" in text


def test_reviewed_dialog_has_no_selection_activation_or_runtime_calls():
    text = APP.read_text(encoding="utf-8")
    start = text.index("        def open_reviewed_import_workflow()")
    end = text.index('        pack_list.bind("<<ListboxSelect>>"', start)
    block = text[start:end]
    for forbidden in (
        "select_paper_pack(",
        "clear_paper_selection(",
        "prepare_canonical_runtime_cutover(",
        "controller.start(",
        "controller.stop(",
        "write_runtime(",
    ):
        assert forbidden not in block


def test_workflow_source_has_no_dynamic_import_or_execution_authority():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "install_approved_metadata(" in text
    assert "OfflineStrategyPackageQuarantine" in text
    for forbidden in (
        "importlib",
        "exec(",
        "eval(",
        "subprocess",
        "os.system",
        "select_paper_pack",
        "prepare_canonical_runtime_cutover",
        "broker.place_order",
    ):
        assert forbidden not in text
