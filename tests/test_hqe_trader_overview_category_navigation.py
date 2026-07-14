from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def run_gui() -> ast.FunctionDef:
    tree = ast.parse(source())
    found = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_gui"
    ]
    assert len(found) == 1
    return found[0]


def button_texts_for_parent(parent: str) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(run_gui()):
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
            and node.args[0].id == parent
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


def test_sidebar_has_trader_categories():
    text = source()
    required = (
        '"Overview"',
        '"Broker Connect"',
        '"Paper Watch"',
        '"Daily Operations"',
        '"Today Report"',
        '"Reports & Evidence"',
        '"System Safety"',
        '"Advanced Tools"',
    )
    assert all(marker in text for marker in required)


def test_category_dispatch_is_wired():
    text = source()
    required = (
        'page_name == "Daily Operations"',
        "show_daily_operations_page()",
        'page_name == "Reports & Evidence"',
        "show_reports_evidence_page()",
        'page_name == "Advanced Tools"',
        "show_advanced_tools_page()",
    )
    assert all(marker in text for marker in required)


def test_overview_runtime_rebuild_removes_legacy_controls():
    text = source()
    assert "HQE_TRADER_OVERVIEW_SIMPLE_CONTROLS_V2" in text
    assert (
        "for _legacy_overview_child "
        "in action_panel.winfo_children()"
    ) in text
    assert "_legacy_overview_child.destroy()" in text


def test_overview_has_only_four_new_trader_controls():
    assert button_texts_for_parent(
        "trader_quick_actions"
    ) == {
        "Refresh Status",
        "Start Paper Trading",
        "Stop Paper Trading",
        "Open Daily Report",
    }


def test_embedded_live_status_is_at_overview_bottom():
    text = source()
    required = (
        "trader_embedded_status.pack(",
        'side="bottom"',
        'text="Embedded Live Status"',
        "textvariable=daily_ops_status",
    )
    assert all(marker in text for marker in required)


def test_running_internet_and_paper_watch_cards_turn_green():
    text = source()
    required = (
        "def _set_trader_status_card_health",
        "def _refresh_trader_status_card_health",
        '"internet": 0',
        '"watch": 3',
        '"#0b3b2e"',
        'palette["safe"]',
        "running = controller.is_running()",
        "running and internet_online",
        "def start_paper_trading",
        "start_watch()",
    )
    assert all(marker in text for marker in required)


def test_removed_overview_actions_are_distributed():
    text = source()
    required = (
        "HQE_TRADER_CATEGORY_BROKER_ACTIONS_V2",
        "Refresh Broker/Data Health",
        "Run Safe Data Test",
        "HQE_TRADER_CATEGORY_PAPER_ACTIONS_V2",
        "Open Paper-Watch Session Control",
        "Daily Startup & Checklist",
        "Prepare Next Market Day",
        "Run Day Rollover Guard",
        "Daily Close & Report",
        "Generate Daily Close Report",
        "Refresh Daily Report",
        "Open Technical Evidence",
        "Open Evidence Folder",
        "Session History & Evidence",
        "HQE_TRADER_CATEGORY_SAFETY_ACTIONS_V2",
        "Open Safety & Kill-Switch Evidence",
        "Advanced Tools Hub",
    )
    assert all(marker in text for marker in required)


def test_change_does_not_add_broker_execution_calls():
    text = source()
    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
    )
    assert not any(marker in text for marker in forbidden)

def test_category_canvas_refits_after_page_layout():
    text = source()
    required = (
        "HQE_CATEGORY_CANVAS_VISIBLE_WIDTH_V2",
        "category_shell.update_idletasks()",
        "page_panel.update_idletasks()",
        "category_scrollbar.winfo_reqwidth()",
        "category_shell.winfo_width()",
        "page_panel.winfo_width()",
        "category_inner.bind(",
        "category_canvas.bind(",
        "category_shell.bind(",
        "page_panel.bind(",
        '"<Configure>"',
        '"<Map>"',
        "root.after_idle(_sync_category_scroll)",
        "root.after(80, _sync_category_scroll)",
        "root.after(250, _sync_category_scroll)",
    )
    assert all(marker in text for marker in required)

