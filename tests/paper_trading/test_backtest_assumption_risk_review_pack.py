import json
from pathlib import Path

from src.paper_trading.backtest_assumption_risk_review_pack import (
    build_and_write_assumption_risk_report,
    build_assumption_risk_report,
    live_trading_rejection_notice,
    no_profitability_claim_notice,
    safety_notice,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _base_files(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "result_review": tmp_path / "result_review.json",
        "ledger": tmp_path / "ledger.json",
        "metrics": tmp_path / "metrics.json",
    }

    _write_json(
        paths["result_review"],
        {
            "status": "pass",
            "ledger_trade_count": 2,
            "metric_trade_count": 2,
            "ce_trade_count": 1,
            "pe_trade_count": 1,
            "winning_trade_count": 1,
            "losing_trade_count": 1,
            "flat_trade_count": 0,
            "win_rate_percent": 50.0,
            "simulated_gross_result_total": 100.0,
            "final_equity_reference": 100100.0,
            "max_drawdown_percent_reference": 12.0,
            "max_drawdown_reference": 1200.0,
            "expectancy_per_trade_reference": 50.0,
            "target_exit_count": 1,
            "stop_loss_exit_count": 1,
            "max_holding_exit_count": 0,
            "other_exit_count": 0,
            "deterministic_pricing_warning": "Deterministic option reference prices, not real option-chain fills.",
        },
    )

    _write_json(
        paths["ledger"],
        {
            "status": "pass",
            "ledger_trade_count": 2,
            "ledger_rows": [
                {"exit_reason": "target_points_reached"},
                {"exit_reason": "stop_loss_points_reached"},
            ],
        },
    )

    _write_json(
        paths["metrics"],
        {
            "status": "pass",
            "metric_trade_count": 2,
        },
    )

    return paths


def test_assumption_risk_review_passes_with_valid_result_review(tmp_path):
    paths = _base_files(tmp_path)

    report, outputs = build_and_write_assumption_risk_report(
        result_review_path=paths["result_review"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.accepted_for_future_tuning_plan is True
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert report.high_risk_item_count >= 1
    assert outputs["risk_json"].exists()
    assert outputs["risk_csv"].exists()
    assert outputs["summary_csv"].exists()

    payload = json.loads(outputs["risk_json"].read_text(encoding="utf-8"))
    assert payload["profitability_claim_allowed"] is False
    assert payload["ready_for_live_or_real_money"] is False


def test_assumption_risk_review_fails_when_result_review_missing(tmp_path):
    paths = _base_files(tmp_path)
    paths["result_review"].unlink()

    report = build_assumption_risk_report(
        result_review_path=paths["result_review"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "result_review_missing" for issue in report.issues)


def test_assumption_risk_review_fails_when_result_review_not_pass(tmp_path):
    paths = _base_files(tmp_path)

    payload = json.loads(paths["result_review"].read_text(encoding="utf-8"))
    payload["status"] = "fail"
    _write_json(paths["result_review"], payload)

    report = build_assumption_risk_report(
        result_review_path=paths["result_review"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "result_review_not_pass" for issue in report.issues)


def test_assumption_risk_review_fails_when_no_trades(tmp_path):
    paths = _base_files(tmp_path)

    payload = json.loads(paths["result_review"].read_text(encoding="utf-8"))
    payload["ledger_trade_count"] = 0
    payload["metric_trade_count"] = 0
    _write_json(paths["result_review"], payload)

    report = build_assumption_risk_report(
        result_review_path=paths["result_review"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_ledger_trades" for issue in report.issues)
    assert any(issue.code == "insufficient_metric_trades" for issue in report.issues)


def test_assumption_risk_items_include_required_categories(tmp_path):
    paths = _base_files(tmp_path)

    report = build_assumption_risk_report(
        result_review_path=paths["result_review"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        output_dir=tmp_path / "out",
    )

    categories = {item.category for item in report.risk_items}

    assert "deterministic_option_reference_pricing" in categories
    assert "real_execution_absent" in categories
    assert "trade_frequency" in categories
    assert "exit_rule_distribution" in categories
    assert "single_recorded_dataset_scope" in categories
    assert "paper_result_interpretation" in categories


def test_assumption_risk_language_rejects_live_and_profit_claims():
    combined = " ".join(
        [
            safety_notice(),
            no_profitability_claim_notice(),
            live_trading_rejection_notice(),
        ]
    ).lower()

    assert "paper/simulation" in combined
    assert "does not connect to brokers" in combined
    assert "place real orders" in combined
    assert "use real money" in combined
    assert "not a profitability claim" in combined
    assert "does not approve live trading" in combined
