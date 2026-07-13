from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return SCRIPT.read_text(encoding="utf-8-sig")


def test_sidebar_uses_real_navigation_buttons():
    text = source()
    assert "nav_buttons: dict[str, tk.Button]" in text
    assert 'command=lambda value=item: navigation_command(value)' in text
    assert 'cursor="hand2"' in text


def test_all_required_app_pages_are_present():
    text = source()
    for function_name in (
        "show_overview_page",
        "show_broker_page",
        "show_paper_watch_page",
        "show_report_page",
        "show_safety_page",
        "show_page",
    ):
        assert f"def {function_name}(" in text


def test_paper_watch_page_has_app_native_controls():
    text = source()
    assert 'text="Start Paper Watch"' in text
    assert 'text="Stop Paper Watch"' in text
    assert 'text="Refresh Status"' in text
    assert 'text="Open Live Status Dashboard"' in text


def test_report_and_evidence_actions_are_app_native():
    text = source()
    assert 'text="Open Trader Report"' in text
    assert 'text="Open Evidence Folder"' in text
    assert 'text="Refresh Trader Report"' in text


def test_guided_tools_prefer_pythonw():
    text = source()
    assert text.count('"pythonw.exe"') >= 2


def test_safety_page_keeps_real_execution_locked():
    text = source()
    assert '("Real money", "DISABLED")' in text
    assert '("Real broker orders", "HARD BLOCKED")' in text
    assert '("Broker execution", "HARD BLOCKED")' in text
    assert '("Automatic trading", "DISABLED")' in text
    assert '("Option selling", "DISABLED")' in text


def test_overview_is_initialized_before_mainloop():
    text = source()
    assert 'show_page("Overview")\n    refresh_status_async()' in text
