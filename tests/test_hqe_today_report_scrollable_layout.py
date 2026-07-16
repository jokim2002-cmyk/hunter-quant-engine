from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def function_source(name: str) -> str:
    text = source()
    tree = ast.parse(text)
    found = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == name
    ]
    assert len(found) == 1
    return ast.get_source_segment(text, found[0]) or ""


def overview_button_texts() -> set[str]:
    text = source()
    tree = ast.parse(text)
    result: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not (
            isinstance(function, ast.Attribute)
            and function.attr == "Button"
            and isinstance(function.value, ast.Name)
            and function.value.id == "ttk"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id
            in {"trader_quick_actions", "trader_overview_actions"}
        ):
            continue
        for keyword in node.keywords:
            if (
                keyword.arg == "text"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                result.add(keyword.value.value)

    return result


def test_today_report_has_full_vertical_scroll():
    text = function_source("show_report_page")
    required = (
        "HQE_TODAY_REPORT_SCROLLABLE_COMPACT_V1",
        "today_report_scroll_canvas",
        "today_report_scrollbar",
        "today_report_inner",
        "scrollregion",
        "<MouseWheel>",
        "<Button-4>",
        "<Button-5>",
        "root.after_idle(_sync_today_report_scroll)",
    )
    assert all(marker in text for marker in required)


def test_today_report_uses_compact_summary_and_grid_buttons():
    text = function_source("show_report_page")
    required = (
        "Actual Paper Trading Position & P&L",
        "summary_grid",
        "def summary_field",
        "Unrealized P&L",
        "Realized P&L",
        "Completed trades",
        "today_actions.grid_columnconfigure",
        "Open Paper Ledger / History",
        "Refresh Today Report",
    )
    assert all(marker in text for marker in required)


def test_overview_opens_embedded_today_report():
    labels = overview_button_texts()
    assert "Open Today Report" in labels
    assert "Open Daily Report" not in labels

    text = source()
    assert 'lambda: show_page("Today Report")' in text


def test_safety_scope_remains_paper_only():
    text = source()
    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
    )
    assert not any(marker in text for marker in forbidden)
