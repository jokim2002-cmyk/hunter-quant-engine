import json
from pathlib import Path

from src.paper_trading.paper_tuning_candidate_readiness_pack import (
    MANDATORY_CANDIDATE_IDS,
    build_and_write_tuning_readiness_report,
    build_tuning_readiness_report,
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
        "risk_review": tmp_path / "risk_review.json",
    }

    _write_json(
        paths["result_review"],
        {
            "status": "pass",
            "accepted_for_future_tuning_review": True,
            "ledger_trade_count": 1800,
            "metric_trade_count": 1800,
            "win_rate_percent": 49.1667,
            "simulated_gross_result_total": 180625.0,
            "max_drawdown_percent_reference": 11.8692,
        },
    )

    _write_json(
        paths["risk_review"],
        {
            "status": "pass",
            "accepted_for_future_tuning_plan": True,
            "ready_for_live_or_real_money": False,
            "profitability_claim_allowed": False,
            "high_risk_item_count": 5,
            "medium_risk_item_count": 2,
            "low_risk_item_count": 1,
            "risk_items": [
                {"category": "deterministic_option_reference_pricing"},
                {"category": "real_execution_absent"},
                {"category": "trade_frequency"},
                {"category": "exit_rule_distribution"},
                {"category": "single_recorded_dataset_scope"},
                {"category": "drawdown_reference"},
                {"category": "paper_result_interpretation"},
                {"category": "option_buy_direction_mapping"},
            ],
        },
    )

    return paths


def test_tuning_readiness_passes_with_valid_inputs(tmp_path):
    paths = _base_files(tmp_path)

    report, outputs = build_and_write_tuning_readiness_report(
        result_review_path=paths["result_review"],
        risk_review_path=paths["risk_review"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.accepted_for_future_paper_tuning_sprint is True
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.candidate_count >= 6
    assert outputs["review_json"].exists()
    assert outputs["candidates_csv"].exists()
    assert outputs["summary_csv"].exists()

    candidate_ids = {candidate.candidate_id for candidate in report.candidates}
    assert MANDATORY_CANDIDATE_IDS.issubset(candidate_ids)


def test_tuning_readiness_fails_when_result_review_missing(tmp_path):
    paths = _base_files(tmp_path)
    paths["result_review"].unlink()

    report = build_tuning_readiness_report(
        result_review_path=paths["result_review"],
        risk_review_path=paths["risk_review"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "result_review_missing" for issue in report.issues)


def test_tuning_readiness_fails_when_risk_review_not_pass(tmp_path):
    paths = _base_files(tmp_path)

    payload = json.loads(paths["risk_review"].read_text(encoding="utf-8"))
    payload["status"] = "fail"
    _write_json(paths["risk_review"], payload)

    report = build_tuning_readiness_report(
        result_review_path=paths["result_review"],
        risk_review_path=paths["risk_review"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "risk_review_not_pass" for issue in report.issues)


def test_tuning_readiness_rejects_live_or_profitability_allowed(tmp_path):
    paths = _base_files(tmp_path)

    payload = json.loads(paths["risk_review"].read_text(encoding="utf-8"))
    payload["ready_for_live_or_real_money"] = True
    payload["profitability_claim_allowed"] = True
    _write_json(paths["risk_review"], payload)

    report = build_tuning_readiness_report(
        result_review_path=paths["result_review"],
        risk_review_path=paths["risk_review"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "risk_review_allows_live_or_real_money" for issue in report.issues)
    assert any(issue.code == "risk_review_allows_profitability_claim" for issue in report.issues)


def test_tuning_candidates_have_live_blocking_reasons(tmp_path):
    paths = _base_files(tmp_path)

    report = build_tuning_readiness_report(
        result_review_path=paths["result_review"],
        risk_review_path=paths["risk_review"],
        output_dir=tmp_path / "out",
    )

    assert report.candidates
    assert all(candidate.blocked_live_usage_reason for candidate in report.candidates)
    assert all(candidate.status == "paper_candidate_ready" for candidate in report.candidates)


def test_tuning_readiness_language_preserves_safety_guards():
    combined = " ".join(
        [
            safety_notice(),
            no_profitability_claim_notice(),
            live_trading_rejection_notice(),
        ]
    ).lower()

    assert "paper/simulation" in combined
    assert "does not" in combined
    assert "connect to brokers" in combined
    assert "place real orders" in combined
    assert "use real money" in combined
    assert "not a profitability claim" in combined
    assert "live trading and real-money usage remain blocked" in combined
