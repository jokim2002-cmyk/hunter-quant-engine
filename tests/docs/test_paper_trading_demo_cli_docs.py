"""
Tests for paper trading demo CLI documentation command sync.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLI_MODULE_COMMAND = r".\.venv\Scripts\python.exe -m src.paper_trading.paper_trading_demo_cli"
SCRIPT_WRAPPER_COMMAND = r".\.venv\Scripts\python.exe examples\run_paper_trading_demo.py"


def test_paper_trading_demo_cli_documented_commands_stay_in_sync():
    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    cli_doc_text = (
        PROJECT_ROOT / "docs" / "PAPER_TRADING_DEMO_CLI.md"
    ).read_text(encoding="utf-8")
    cli_source = (
        PROJECT_ROOT / "src" / "paper_trading" / "paper_trading_demo_cli.py"
    ).read_text(encoding="utf-8")
    wrapper_source = (
        PROJECT_ROOT / "examples" / "run_paper_trading_demo.py"
    ).read_text(encoding="utf-8")

    assert CLI_MODULE_COMMAND in readme_text
    assert CLI_MODULE_COMMAND in cli_doc_text
    assert SCRIPT_WRAPPER_COMMAND in readme_text
    assert SCRIPT_WRAPPER_COMMAND in cli_doc_text

    assert "def main() -> int:" in cli_source
    assert (
        "from src.paper_trading.paper_trading_demo_cli import main, run_demo"
        in wrapper_source
    )
