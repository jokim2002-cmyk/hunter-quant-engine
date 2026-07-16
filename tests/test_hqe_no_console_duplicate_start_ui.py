from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"
WATCH = REPO / "scripts" / "hqe_market_day_persistent_paper_watch_loop.py"
CYCLE = REPO / "scripts" / "hqe_current_day_live_data_cycle.py"


def function_source(path: Path, name: str) -> str:
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == name
    ]
    assert len(matches) == 1
    return ast.get_source_segment(text, matches[0]) or ""


def test_duplicate_start_has_distinct_operator_message():
    source = function_source(APP, "start_watch")
    for marker in (
        "ALREADY_RUNNING_CANONICAL",
        "ALREADY_RUNNING_GLOBAL",
        "ALREADY_RUNNING_IN_APP",
        "Duplicate start was blocked safely",
        "No second runtime was started",
    ):
        assert marker in source


def test_duplicate_start_path_does_not_claim_new_start():
    source = function_source(APP, "start_watch")
    duplicate_position = source.index("if status in duplicate_statuses")
    started_position = source.index("if result.get(\"started\")")
    assert duplicate_position < started_position
    assert "return" in source[duplicate_position:started_position]


def test_persistent_watch_data_fetch_hides_windows_console():
    source = function_source(WATCH, "run_data_fetch")
    assert "creationflags=CREATE_NO_WINDOW" in source
    assert "subprocess.run" in source


def test_current_day_live_cycle_hides_windows_console():
    source = function_source(CYCLE, "run_cycle")
    assert "creationflags=CREATE_NO_WINDOW" in source
    assert "subprocess.run" in source


def test_no_console_constants_are_platform_safe():
    for path in (WATCH, CYCLE):
        text = path.read_text(encoding="utf-8-sig")
        assert 'CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0' in text
        ast.parse(text)
