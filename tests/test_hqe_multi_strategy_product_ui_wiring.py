from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "scripts" / "hqe_product_app_v2.py"
REHEARSAL = ROOT / "scripts" / "hqe_multi_strategy_phase5_product_ui_rehearsal.py"


def source() -> str:
    return APP.read_text(encoding="utf-8")


def test_app_imports_product_strategy_manager_model():
    text = source()
    bootstrap = "REPO_ROOT = Path(__file__).resolve().parents[1]"
    manager_import = "from src.multi_strategy.product_ui_manager import ("
    assert bootstrap in text
    assert "sys.path.insert(0, str(REPO_ROOT))" in text
    assert text.index(bootstrap) < text.index(manager_import)
    assert manager_import in text
    for name in (
        "build_product_strategy_manager_snapshot",
        "evaluate_clear_configuration",
        "evaluate_configuration_selection",
        "guard_payload as product_strategy_manager_guard_payload",
    ):
        assert name in text

    rehearsal_text = REHEARSAL.read_text(encoding="utf-8")
    assert bootstrap in rehearsal_text
    assert "sys.path.insert(0, str(REPO_ROOT))" in rehearsal_text
    assert rehearsal_text.index(bootstrap) < rehearsal_text.index(
        "from src.multi_strategy.product_ui_manager import ("
    )


def test_app_has_visible_product_strategy_manager_center():
    text = source()
    assert "def open_product_strategy_manager_center()" in text
    assert "Product Strategy Manager" in text
    assert "Select for Paper Configuration" in text
    assert "Clear Paper Configuration" in text
    assert "Canonical activation remains separately human-gated" in text


def test_manager_uses_runtime_and_position_guards():
    text = source()
    assert "runtime_running=controller.is_running()" in text
    assert "paper_product_snapshot(workspace)" in text
    assert "evaluate_configuration_selection" in text
    assert "evaluate_clear_configuration" in text


def test_manager_does_not_create_human_gate_or_start_runtime():
    tree = ast.parse(source())
    manager = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "open_product_strategy_manager_center"
    )
    calls = {
        node.func.id
        for node in ast.walk(manager)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "write_human_gate" not in calls
    assert "prepare_canonical_runtime_cutover" not in calls
    assert "start_watch" not in calls
    assert "stop_watch" not in calls


def test_advanced_tools_smoke_requires_manager():
    text = source()
    required_line = next(
        line for line in text.splitlines()
        if "required = (" in line and "Operator Dashboard" in line
    )
    assert "Product Strategy Manager" in required_line


def test_app_guard_exposes_phase5_guard():
    text = source()
    assert '"multi_strategy_phase5_product_ui":' in text
    assert "product_strategy_manager_guard_payload()" in text
