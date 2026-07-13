from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def load_tree() -> ast.Module:
    return ast.parse(APP.read_text(encoding="utf-8-sig"))


def button_records() -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    for node in ast.walk(load_tree()):
        if not isinstance(node, ast.Call):
            continue

        button_call = None
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "pack"
            and isinstance(node.func.value, ast.Call)
        ):
            button_call = node.func.value
        elif isinstance(node.func, ast.Attribute):
            button_call = node

        if button_call is None:
            continue
        if not (
            isinstance(button_call.func, ast.Attribute)
            and button_call.func.attr == "Button"
        ):
            continue

        text_value = ""
        command_name = ""
        for keyword in button_call.keywords:
            if keyword.arg == "text" and isinstance(
                keyword.value,
                ast.Constant,
            ):
                text_value = str(keyword.value.value)
            elif keyword.arg == "command":
                if isinstance(keyword.value, ast.Name):
                    command_name = keyword.value.id
                elif isinstance(keyword.value, ast.Attribute):
                    command_name = keyword.value.attr

        if text_value:
            records.append((text_value, command_name))
    return records


def test_direct_fyers_token_refresh_button_is_wired():
    records = button_records()
    assert (
        "Fyers Login & Token Refresh",
        "open_fyers_auth_dialog",
    ) in records
    assert (
        "Open Guided Broker Connect",
        "open_broker_connect_center",
    ) in records


def test_auth_dialog_exists_and_remains_data_only():
    text = APP.read_text(encoding="utf-8-sig")
    assert "def open_fyers_auth_dialog" in text
    assert "Credentials are encrypted with Windows DPAPI." in text
    assert (
        "Real orders and broker execution remain permanently blocked."
        in text
    )

    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
    )
    assert not any(marker in text for marker in forbidden)


def test_app_parses_after_button_insertion():
    load_tree()
