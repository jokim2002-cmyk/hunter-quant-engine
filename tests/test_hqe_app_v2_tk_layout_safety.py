from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def call_name(call: ast.Call) -> str:
    function = call.func
    if isinstance(function, ast.Attribute):
        return function.attr
    if isinstance(function, ast.Name):
        return function.id
    return ""


def test_tk_label_widget_padding_is_scalar():
    tree = ast.parse(APP.read_text(encoding="utf-8-sig"))
    failures: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if call_name(node) != "Label":
            continue
        for keyword in node.keywords:
            if keyword.arg not in {"padx", "pady"}:
                continue
            if isinstance(keyword.value, (ast.Tuple, ast.List)):
                failures.append(
                    f"line {node.lineno}: "
                    f"tk.Label {keyword.arg} must be scalar"
                )

    assert not failures, "\n".join(failures)
