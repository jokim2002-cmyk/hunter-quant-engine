import json
from pathlib import Path

from src.paper_trading.real_recorded_backtest_result_review_pack import (
    build_and_write_result_review_report,
    build_result_review_report,
    deterministic_pricing_warning,
    no_profitability_claim_notice,
    safety_notice,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _base_files(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "readiness": tmp_path / "readiness.json",
        "acceptance": tmp_path / "acceptance.json",
        "runner": tmp_path / "runner.json",
        "ledger": tmp_path / "ledger.json",
        "metrics": tmp_path / "metrics.json",
        "backtest_report": tmp_path / "backtest_report.json",
    }

    _write_json(
        paths["readiness"],
        {"status": "pass", "ready_for_future_v1_testing_release_gate": True},
    )
    _write_json(paths["acceptance"], {"status": "pass"})
    _write_json(paths["runner"], {"status": "pass"})
    _write_json(paths["backtest_report"], {"status": "pass"})

    _write_json(
        paths["ledger"],
        {
            "status": "pass",
            "ledger_trade_count": 2,
            "ce_trade_count": 1,
            "pe_trade_count": 1,
            "ledger_rows": [
                {
                    "decision": "LONG",
                    "option_type": "CE",
                    "option_action": "BUY",
                    "broker_execution_mode": "broker_disabled",
                    "order_mode": "orders_not_created",
                    "money_mode": "real_money_not_used",
                    "exit_reason": "target_points_reached",
                },
                {
                    "decision": "SHORT",
                    "option_type": "PE",
                    "option_action": "BUY",
                    "broker_execution_mode": "broker_disabled",
                    "order_mode": "orders_not_created",
                    "money_mode": "real_money_not_used",
                    "exit_reason": "stop_loss_points_reached",
                },
            ],
        },
    )

    _write_json(
        paths["metrics"],
        {
            "status": "pass",
            "metric_trade_count": 2,
            "winning_trade_count": 1,
            "losing_trade_count": 1,
            "flat_trade_count": 0,
            "win_rate_percent": 50.0,
            "loss_rate_percent": 50.0,
            "flat_rate_percent": 0.0,
            "simulated_gross_result_total": 100.0,
            "starting_equity_reference": 100000.0,
            "final_equity_reference": 100100.0,
            "max_drawdown_reference": 50.0,
            "max_drawdown_percent_reference": 0.05,
            "expectancy_per_trade_reference": 50.0,
            "largest_winning_trade_result": 200.0,
            "largest_losing_trade_result": -100.0,
        },
    )

    return paths


def test_review_pack_passes_with_safe_paper_outputs(tmp_path):
    paths = _base_files(tmp_path)

    report, outputs = build_and_write_result_review_report(
        readiness_path=paths["readiness"],
        acceptance_path=paths["acceptance"],
        runner_path=paths["runner"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        backtest_report_path=paths["backtest_report"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.accepted_for_future_tuning_review is True
    assert report.ledger_trade_count == 2
    assert report.metric_trade_count == 2
    assert report.long_ce_buy_count == 1
    assert report.short_pe_buy_count == 1
    assert report.invalid_direction_mapping_count == 0
    assert report.unsafe_broker_mode_count == 0
    assert outputs["review_json"].exists()
    assert outputs["checklist_csv"].exists()
    assert outputs["summary_csv"].exists()

    payload = json.loads(outputs["review_json"].read_text(encoding="utf-8"))
    assert payload["no_profitability_claim_notice"]
    assert payload["deterministic_pricing_warning"]


def test_review_pack_fails_when_required_file_missing(tmp_path):
    paths = _base_files(tmp_path)
    paths["ledger"].unlink()

    report = build_result_review_report(
        readiness_path=paths["readiness"],
        acceptance_path=paths["acceptance"],
        runner_path=paths["runner"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        backtest_report_path=paths["backtest_report"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "ledger_report_missing" for issue in report.issues)


def test_review_pack_rejects_unsafe_broker_rows(tmp_path):
    paths = _base_files(tmp_path)

    ledger = json.loads(paths["ledger"].read_text(encoding="utf-8"))
    ledger["ledger_rows"][0]["broker_execution_mode"] = "broker_enabled"
    _write_json(paths["ledger"], ledger)

    report = build_result_review_report(
        readiness_path=paths["readiness"],
        acceptance_path=paths["acceptance"],
        runner_path=paths["runner"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        backtest_report_path=paths["backtest_report"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.unsafe_broker_mode_count == 1
    assert any(issue.code == "unsafe_broker_mode_rows" for issue in report.issues)


def test_review_pack_rejects_invalid_direction_mapping(tmp_path):
    paths = _base_files(tmp_path)

    ledger = json.loads(paths["ledger"].read_text(encoding="utf-8"))
    ledger["ledger_rows"][0]["option_type"] = "PE"
    _write_json(paths["ledger"], ledger)

    report = build_result_review_report(
        readiness_path=paths["readiness"],
        acceptance_path=paths["acceptance"],
        runner_path=paths["runner"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        backtest_report_path=paths["backtest_report"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.invalid_direction_mapping_count == 1
    assert any(
        issue.code == "invalid_option_buy_direction_mapping"
        for issue in report.issues
    )


def test_review_pack_requires_pass_statuses(tmp_path):
    paths = _base_files(tmp_path)

    _write_json(paths["metrics"], {"status": "fail", "metric_trade_count": 2})

    report = build_result_review_report(
        readiness_path=paths["readiness"],
        acceptance_path=paths["acceptance"],
        runner_path=paths["runner"],
        ledger_path=paths["ledger"],
        metrics_path=paths["metrics"],
        backtest_report_path=paths["backtest_report"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "metrics_report_not_pass" for issue in report.issues)


def test_review_language_preserves_safety_and_no_profit_claim():
    combined = " ".join(
        [
            safety_notice(),
            no_profitability_claim_notice(),
            deterministic_pricing_warning(),
        ]
    ).lower()

    assert "paper/simulation" in combined
    assert "does not connect to brokers" in combined
    assert "place real orders" in combined
    assert "use real money" in combined
    assert "not a profitability claim" in combined
    assert "deterministic" in combined
    assert "not real option-chain fills" in combined
