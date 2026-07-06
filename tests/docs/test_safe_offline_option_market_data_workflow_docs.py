from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_readme_documents_safe_offline_option_market_data_workflow():
    text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Safe Offline Option Market Data Workflow" in text
    assert "Synthetic in-memory recording demo" in text
    assert "CSV validation demo" in text
    assert "CSV replay demo" in text
    assert "End-to-end record -> validate -> replay smoke test" in text
    assert "Does not use FYERS" in text
    assert "Does not use live or real market data" in text
    assert "Does not place orders" in text
    assert "Is not a profitability claim" in text
    assert "examples/record_in_memory_option_market_data.py" in text
    assert "tests/examples/test_option_market_data_demo_workflow.py" in text


def test_roadmap_documents_safe_offline_option_market_data_workflow_checkpoint():
    text = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8")

    assert "Completed Checkpoint" in text
    assert "Safe Offline Option Market Data Workflow" in text
    assert "Synthetic in-memory recording demo" in text
    assert "CSV validation demo" in text
    assert "CSV replay demo" in text
    assert "End-to-end record -> validate -> replay smoke test" in text
    assert "Broker-agnostic" in text
    assert "No FYERS" in text
    assert "No live or real market data" in text
    assert "No orders" in text
    assert "No profitability claim" in text
    assert "Future phase" in text
    assert "Real broker/live data adapter after safety layers" in text
