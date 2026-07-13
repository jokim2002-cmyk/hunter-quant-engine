from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def parsed_app() -> tuple[str, ast.Module]:
    source = APP.read_text(encoding="utf-8-sig")
    return source, ast.parse(source)


def test_startup_refresh_is_backgrounded():
    source, _tree = parsed_app()
    assert "def refresh_status_async() -> None:" in source
    assert "threading.Thread(target=worker, daemon=True).start()" in source
    assert "root.after(0, apply_result)" in source


def test_initial_and_scheduled_refresh_use_async_path():
    source, _tree = parsed_app()
    startup = source[source.index('root.protocol("WM_DELETE_WINDOW", close_app)'):]
    assert 'show_page("Overview")\n    refresh_status_async()' in startup
    assert "root.after(15000, refresh_status_async)" in startup
    assert 'show_page("Overview")\n    refresh_status()' not in startup


def test_import_profile_remains_lightweight():
    source, _tree = parsed_app()
    assert "internet_status(timeout_seconds: float = 1.5)" in source
    assert "refresh_status_async" in source
